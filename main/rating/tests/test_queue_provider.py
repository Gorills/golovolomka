import os
import uuid
from datetime import timedelta
from unittest import mock

import requests
from django.test import TestCase, override_settings
from django.utils import timezone

from rating.models import MessageAttempt, MessageDelivery, SmsIntegrationSettings
from rating.provider import ProviderResult, SmsPilotClient
from rating.queue import poll_batch, process_batch, recover_stale_leases
from rating.secrets import decrypt_secret, encrypt_secret, get_sms_api_key
from rating.services import ConcurrencyConflict, ValidationError, request_manual_retry, sms_parts

from .factories import city, delivery_for, score, team, user


class Response:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError()


@override_settings(RATING_SECRET_ENCRYPTION_KEY='test-only-master')
class QueueProviderTests(TestCase):
    def setUp(self):
        self.city = city()
        self.actor = user(city_obj=self.city)
        self.team = team(self.actor, self.city)
        self.score = score(self.team)
        self.integration = SmsIntegrationSettings.get_solo()
        self.integration.sending_enabled = True
        self.integration.emergency_stop = False
        self.integration.test_mode = True
        self.integration.save()

    def test_cyrillic_sms_parts_use_70_and_67_limits(self):
        self.assertEqual(sms_parts('я' * 70), 1)
        self.assertEqual(sms_parts('я' * 71), 2)
        self.assertEqual(sms_parts('я' * 134), 2)
        self.assertEqual(sms_parts('я' * 135), 3)

    def test_provider_sends_test_flag_and_maps_documented_statuses(self):
        delivery = delivery_for(self.score)
        for raw, expected in (
            (-2, MessageDelivery.Status.FAILED),
            (-1, MessageDelivery.Status.FAILED),
            (0, MessageDelivery.Status.ACCEPTED),
            (1, MessageDelivery.Status.ACCEPTED),
            (2, MessageDelivery.Status.DELIVERED),
            (3, MessageDelivery.Status.UNKNOWN),
        ):
            with self.subTest(raw=raw), mock.patch('rating.provider.requests.post') as post:
                post.return_value = Response({'send': [{'id': 'provider-id', 'status': raw}]})
                result = SmsPilotClient(api_key='secret').send(delivery, test_mode=True)
                self.assertEqual(result.status, expected)
                sent = post.call_args.kwargs['data']
                self.assertEqual(sent['test'], '1')
                self.assertEqual(sent['to'], '79990000000')
                self.assertEqual(sent['apikey'], 'secret')

    def test_connection_ambiguity_is_unknown_and_never_blindly_retried(self):
        delivery = delivery_for(self.score)
        with mock.patch('rating.provider.requests.post', side_effect=requests.ConnectionError):
            result = SmsPilotClient(api_key='secret').send(delivery)
        self.assertEqual(result.status, MessageDelivery.Status.UNKNOWN)
        self.assertFalse(result.safe_to_retry)

    def test_emergency_stop_preserves_queue_and_does_not_call_provider(self):
        delivery = delivery_for(self.score)
        self.integration.emergency_stop = True
        self.integration.save(update_fields=('emergency_stop',))
        fake = mock.Mock()
        result = process_batch(client=fake)
        self.assertEqual(result, {'processed': 0, 'paused': True})
        fake.send.assert_not_called()
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, MessageDelivery.Status.QUEUED)

    def test_worker_empty_body_fails_without_network(self):
        type(self.team).objects.filter(pk=self.team.pk).update(
            phone='+79990000000',
            sms_allowed=True,
            consent_source='registration',
            consent_recorded_at=timezone.now(),
            consent_recorded_by=self.actor,
        )
        delivery = delivery_for(self.score, body='')
        fake = mock.Mock()
        result = process_batch(client=fake)
        self.assertEqual(result['processed'], 1)
        fake.send.assert_not_called()
        delivery.refresh_from_db()
        self.assertEqual((delivery.status, delivery.safe_error_code), (MessageDelivery.Status.FAILED, 'template_missing'))

    def test_worker_expires_old_queue_without_network(self):
        delivery = delivery_for(self.score)
        delivery.expires_at = timezone.now() - timedelta(seconds=1)
        delivery.save(update_fields=('expires_at',))
        fake = mock.Mock()
        result = process_batch(client=fake)
        self.assertEqual(result['processed'], 0)
        fake.send.assert_not_called()
        delivery.refresh_from_db()
        self.assertEqual(
            (delivery.status, delivery.safe_error_code),
            (MessageDelivery.Status.EXPIRED, 'retry_window_expired'),
        )

    def test_stale_processing_lease_becomes_unknown_for_human_decision(self):
        delivery = delivery_for(self.score, status=MessageDelivery.Status.PROCESSING)
        delivery.lease_token = uuid.uuid4()
        delivery.lease_until = timezone.now() - timedelta(seconds=1)
        delivery.save(update_fields=('lease_token', 'lease_until'))
        self.assertEqual(recover_stale_leases(), 1)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, MessageDelivery.Status.UNKNOWN)
        self.assertIsNone(delivery.lease_token)
        self.assertTrue(
            MessageAttempt.objects.filter(
                delivery=delivery, result_status=MessageDelivery.Status.UNKNOWN
            ).exists()
        )

    def test_dispatch_rechecks_current_consent_and_recipient_before_network(self):
        cases = (
            ('consent_revoked', {'sms_allowed': False}),
            ('missing_phone_current', {'phone': ''}),
            ('recipient_changed', {'phone': '+79991112233'}),
        )
        for index, (error_code, changes) in enumerate(cases):
            with self.subTest(error_code=error_code):
                item = team(
                    self.actor,
                    self.city,
                    name='Получатель {}'.format(index),
                    phone='+79990000000',
                    sms_allowed=True,
                    consent_source='registration',
                    consent_recorded_at=timezone.now(),
                )
                delivery = delivery_for(score(item))
                type(item).objects.filter(pk=item.pk).update(**changes)
                fake = mock.Mock()
                result = process_batch(limit=1, client=fake)
                self.assertEqual(result['processed'], 1)
                fake.send.assert_not_called()
                delivery.refresh_from_db()
                self.assertEqual(
                    (delivery.status, delivery.safe_error_code),
                    (MessageDelivery.Status.SKIPPED, error_code),
                )

    def test_manual_retry_requires_confirmation_for_unknown_and_expires_at_three_days(self):
        delivery = delivery_for(self.score, status=MessageDelivery.Status.UNKNOWN)
        with self.assertRaises(ValidationError):
            request_manual_retry(
                actor=self.actor, delivery=delivery, operation_id=uuid.uuid4(), reason='Проверка'
            )
        attempt, created = request_manual_retry(
            actor=self.actor, delivery=delivery, operation_id=uuid.uuid4(),
            reason='Подтверждено', confirm_unknown=True,
        )
        self.assertTrue(created)
        self.assertEqual(attempt.reason, 'Подтверждено')
        self.assertNotIn('Подтверждено', attempt.safe_error_code)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, MessageDelivery.Status.QUEUED)
        delivery.status = MessageDelivery.Status.FAILED
        delivery.expires_at = timezone.now() - timedelta(seconds=1)
        delivery.save(update_fields=('status', 'expires_at'))
        with self.assertRaises(ValidationError):
            request_manual_retry(
                actor=self.actor, delivery=delivery, operation_id=uuid.uuid4(), reason='Поздно'
            )

    def test_manual_retry_revalidates_locked_status_and_cannot_requeue_delivered(self):
        delivery = delivery_for(self.score, status=MessageDelivery.Status.FAILED)
        stale_delivery = MessageDelivery.objects.get(pk=delivery.pk)
        MessageDelivery.objects.filter(pk=delivery.pk).update(status=MessageDelivery.Status.DELIVERED)
        with self.assertRaises(ConcurrencyConflict):
            request_manual_retry(
                actor=self.actor,
                delivery=stale_delivery,
                operation_id=uuid.uuid4(),
                reason='Устаревшее действие',
            )
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, MessageDelivery.Status.DELIVERED)
        self.assertFalse(MessageAttempt.objects.filter(delivery=delivery).exists())

    def test_poll_result_does_not_overwrite_concurrent_terminal_or_requeued_state(self):
        class RacingClient:
            def __init__(self, replacement_status):
                self.replacement_status = replacement_status

            def poll(self, item):
                MessageDelivery.objects.filter(pk=item.pk).update(status=self.replacement_status)
                return ProviderResult(MessageDelivery.Status.FAILED, 'stale_provider_result')

        for replacement in (MessageDelivery.Status.DELIVERED, MessageDelivery.Status.QUEUED):
            with self.subTest(replacement=replacement):
                delivery = delivery_for(self.score, status=MessageDelivery.Status.ACCEPTED)
                delivery.provider_message_id = 'provider-{}'.format(delivery.pk)
                delivery.save(update_fields=('provider_message_id',))
                poll_batch(client=RacingClient(replacement))
                delivery.refresh_from_db()
                self.assertEqual(delivery.status, replacement)
                self.assertFalse(MessageAttempt.objects.filter(delivery=delivery).exists())

        legitimate = delivery_for(self.score, status=MessageDelivery.Status.ACCEPTED)
        legitimate.provider_message_id = 'provider-legitimate'
        legitimate.save(update_fields=('provider_message_id',))
        client = mock.Mock()
        client.poll.return_value = ProviderResult(
            MessageDelivery.Status.DELIVERED, provider_status_code='2'
        )
        result = poll_batch(client=client)
        self.assertEqual(result['processed'], 1)
        legitimate.refresh_from_db()
        self.assertEqual(legitimate.status, MessageDelivery.Status.DELIVERED)
        self.assertTrue(
            MessageAttempt.objects.filter(
                delivery=legitimate,
                kind=MessageAttempt.Kind.POLL,
                result_status=MessageDelivery.Status.DELIVERED,
            ).exists()
        )

    def test_encrypted_secret_is_write_only_replace_clear_and_env_override(self):
        first = encrypt_secret('first-secret')
        self.assertNotIn('first-secret', first)
        self.assertEqual(decrypt_secret(first), 'first-secret')
        second = encrypt_secret('replacement')
        self.integration.api_key_ciphertext = second
        self.integration.save(update_fields=('api_key_ciphertext',))
        self.assertEqual(get_sms_api_key(), 'replacement')
        with mock.patch.dict(os.environ, {'SMSPILOT_API_KEY': 'environment-secret'}):
            self.assertEqual(get_sms_api_key(), 'environment-secret')
        self.integration.api_key_ciphertext = ''
        self.integration.save(update_fields=('api_key_ciphertext',))
        self.assertEqual(get_sms_api_key(), '')
