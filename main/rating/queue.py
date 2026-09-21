import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from .models import MessageAttempt, MessageDelivery, SmsIntegrationSettings
from .provider import ProviderResult, SmsPilotClient


MAX_AUTO_ATTEMPTS = 3
LEASE_SECONDS = 90


def recover_stale_leases(now=None):
    now = now or timezone.now()
    stale = MessageDelivery.objects.filter(
        status=MessageDelivery.Status.PROCESSING, lease_until__lt=now
    )
    count = 0
    for delivery in stale:
        with transaction.atomic():
            changed = MessageDelivery.objects.filter(
                pk=delivery.pk,
                status=MessageDelivery.Status.PROCESSING,
                lease_token=delivery.lease_token,
            ).update(
                status=MessageDelivery.Status.UNKNOWN,
                safe_error_code='worker_result_unknown',
                lease_token=None,
                lease_until=None,
            )
            if changed:
                MessageAttempt.objects.create(
                    delivery=delivery,
                    kind=MessageAttempt.Kind.AUTO,
                    result_status=MessageDelivery.Status.UNKNOWN,
                    safe_error_code='worker_result_unknown',
                )
                count += 1
    return count


def expire_deliveries(now=None):
    now = now or timezone.now()
    return MessageDelivery.objects.filter(
        status__in=(MessageDelivery.Status.QUEUED, MessageDelivery.Status.FAILED),
        expires_at__lte=now,
    ).update(status=MessageDelivery.Status.EXPIRED, safe_error_code='retry_window_expired')


def claim_one(now=None):
    now = now or timezone.now()
    candidate = (
        MessageDelivery.objects.filter(
            status=MessageDelivery.Status.QUEUED,
            expires_at__gt=now,
        )
        .filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now))
        .order_by('created_at', 'pk')
        .values_list('pk', flat=True)
        .first()
    )
    if candidate is None:
        return None
    token = uuid.uuid4()
    with transaction.atomic():
        changed = MessageDelivery.objects.filter(
            pk=candidate, status=MessageDelivery.Status.QUEUED
        ).update(
            status=MessageDelivery.Status.PROCESSING,
            lease_token=token,
            lease_until=now + timedelta(seconds=LEASE_SECONDS),
            last_attempt_at=now,
            attempt_count=F('attempt_count') + 1,
        )
    if changed != 1:
        return None
    return MessageDelivery.objects.select_related('event__team_score__team').get(
        pk=candidate, lease_token=token
    )


def finish_delivery(delivery, result, now=None):
    now = now or timezone.now()
    delivery.refresh_from_db(fields=('attempt_count',))
    status = result.status
    next_attempt_at = None
    if result.safe_to_retry and delivery.attempt_count < MAX_AUTO_ATTEMPTS:
        status = MessageDelivery.Status.QUEUED
        next_attempt_at = now + timedelta(seconds=30 * (2 ** (delivery.attempt_count - 1)))
    with transaction.atomic():
        changed = MessageDelivery.objects.filter(
            pk=delivery.pk,
            status=MessageDelivery.Status.PROCESSING,
            lease_token=delivery.lease_token,
        ).update(
            status=status,
            safe_error_code=result.safe_error_code,
            provider_message_id=result.provider_message_id or delivery.provider_message_id,
            provider_status_code=result.provider_status_code,
            parts=result.parts or delivery.parts,
            cost=result.cost,
            next_attempt_at=next_attempt_at,
            delivered_at=now if status == MessageDelivery.Status.DELIVERED else None,
            lease_token=None,
            lease_until=None,
        )
        if changed != 1:
            return False
        MessageAttempt.objects.create(
            delivery=delivery,
            kind=MessageAttempt.Kind.AUTO,
            result_status=status,
            safe_error_code=result.safe_error_code,
            provider_status_code=result.provider_status_code,
        )
    return True


def process_batch(limit=50, client=None, now=None):
    now = now or timezone.now()
    integration = SmsIntegrationSettings.get_solo()
    recover_stale_leases(now)
    expire_deliveries(now)
    if not integration.sending_enabled or integration.emergency_stop:
        return {'processed': 0, 'paused': True}
    client = client or SmsPilotClient()
    processed = 0
    for _ in range(max(0, min(int(limit), 500))):
        delivery = claim_one(now)
        if delivery is None:
            break
        team = delivery.event.team_score.team
        if not team.sms_allowed:
            result = ProviderResult(MessageDelivery.Status.SKIPPED, 'consent_revoked')
        elif not team.phone:
            result = ProviderResult(MessageDelivery.Status.SKIPPED, 'missing_phone_current')
        elif team.phone != delivery.recipient:
            result = ProviderResult(MessageDelivery.Status.SKIPPED, 'recipient_changed')
        elif not delivery.rendered_body:
            result = ProviderResult(MessageDelivery.Status.FAILED, 'template_missing')
        else:
            result = client.send(
                delivery,
                sender_name=integration.sender_name,
                test_mode=integration.test_mode,
            )
        finish_delivery(delivery, result, now)
        processed += 1
    return {'processed': processed, 'paused': False}


def poll_batch(limit=100, client=None):
    integration = SmsIntegrationSettings.get_solo()
    if not integration.sending_enabled or integration.emergency_stop:
        return {'processed': 0, 'paused': True}
    client = client or SmsPilotClient()
    queryset = MessageDelivery.objects.filter(
        status__in=(MessageDelivery.Status.ACCEPTED, MessageDelivery.Status.UNKNOWN)
    ).exclude(provider_message_id='').order_by('updated_at', 'pk')[:max(0, min(int(limit), 500))]
    processed = 0
    for delivery in queryset:
        observed_status = delivery.status
        observed_updated_at = delivery.updated_at
        result = client.poll(delivery)
        with transaction.atomic():
            changed = MessageDelivery.objects.filter(
                pk=delivery.pk,
                status=observed_status,
                updated_at=observed_updated_at,
            ).update(
                status=result.status,
                safe_error_code=result.safe_error_code,
                provider_status_code=result.provider_status_code,
                delivered_at=(
                    timezone.now() if result.status == MessageDelivery.Status.DELIVERED else None
                ),
            )
            if changed == 1:
                MessageAttempt.objects.create(
                    delivery=delivery,
                    kind=MessageAttempt.Kind.POLL,
                    result_status=result.status,
                    safe_error_code=result.safe_error_code,
                    provider_status_code=result.provider_status_code,
                )
                processed += 1
    return {'processed': processed, 'paused': False}
