import os
from decimal import Decimal
from unittest import mock

from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from rating.forms import ScoreAdjustmentForm
from rating.models import (
    CityRatingAccess,
    CityRankGift,
    MessageAttempt,
    MessageDelivery,
    RankChangeEvent,
    ScoreAdjustment,
    SmsIntegrationSettings,
    Team,
    TeamRankAchievement,
)
from rating.services import apply_adjustment
from rating.provider import ProviderResult

from .factories import city, delivery_for, operation_id, score, team, user


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '.localhost'])
class RatingHttpAuthorizationTests(TestCase):
    def setUp(self):
        self.city_a = city('nsk')
        self.city_b = city('tomsk')
        self.operator = user(city_obj=self.city_a)
        self.foreign_operator = user('foreign', city_obj=self.city_b)
        self.own_team = team(self.operator, self.city_a, name='Своя команда')
        self.foreign_team = team(self.foreign_operator, self.city_b, name='Чужая команда')

    def test_unauthenticated_redirects_and_inactive_or_accessless_users_are_denied(self):
        url = reverse('rating_admin:team_list')
        self.assertEqual(self.client.get(url).status_code, 302)
        inactive = user('inactive', city_obj=self.city_a, active=False)
        self.client.force_login(inactive)
        response = self.client.get(url)
        self.assertIn(response.status_code, (302, 403))
        self.assertNotContains(response, 'Своя команда', status_code=response.status_code)
        self.client.force_login(user('noaccess'))
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_list_and_search_do_not_disclose_foreign_city(self):
        self.client.force_login(self.operator)
        response = self.client.get(reverse('rating_admin:team_list'), {'q': 'команда'})
        self.assertContains(response, 'Своя команда')
        self.assertNotContains(response, 'Чужая команда')

    def test_foreign_object_id_returns_404_and_has_no_side_effect(self):
        self.client.force_login(self.operator)
        detail = reverse('rating_admin:team_detail', args=[self.foreign_team.pk])
        archive = reverse('rating_admin:team_archive', args=[self.foreign_team.pk])
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertEqual(self.client.post(archive).status_code, 404)
        self.foreign_team.refresh_from_db()
        self.assertTrue(self.foreign_team.is_active)

    def test_inactive_city_access_is_denied(self):
        CityRatingAccess.objects.filter(user=self.operator, city=self.city_a).update(is_active=False)
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get(reverse('rating_admin:team_list')).status_code, 403)

    def test_state_changing_endpoint_rejects_get_and_missing_csrf(self):
        self.client.force_login(self.operator)
        archive = reverse('rating_admin:team_archive', args=[self.own_team.pk])
        self.assertEqual(self.client.get(archive).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.operator)
        self.assertEqual(csrf_client.post(archive).status_code, 403)
        self.own_team.refresh_from_db()
        self.assertTrue(self.own_team.is_active)

    def test_city_selector_rejects_foreign_city_and_external_redirect(self):
        extra = city('omsk')
        CityRatingAccess.objects.create(user=self.operator, city=extra)
        self.client.force_login(self.operator)
        url = reverse('rating_admin:city_select')
        denied = self.client.post(url, {'city': self.city_b.slug})
        self.assertIn(denied.status_code, (400, 404))
        response = self.client.post(
            url, {'city': extra.slug, 'next': 'https://attacker.example/collect'}
        )
        self.assertRedirects(response, reverse('rating_admin:team_list'), fetch_redirect_response=False)

    def test_operator_sees_only_city_gifts_and_cannot_open_global_editors(self):
        self.client.force_login(self.operator)
        catalog = self.client.get(reverse('rating_admin:catalog'))
        self.assertEqual(catalog.status_code, 200)
        self.assertContains(catalog, 'Подарки · {}'.format(self.city_a.name))
        self.assertNotContains(catalog, 'Добавить ранг')
        self.assertNotContains(catalog, 'Публичная страница')

        rating_format = self.own_team.scores.select_related('rating_format').get(
            rating_format__code='classic'
        ).rating_format
        rank = rating_format.ranks.get(level=1)
        original = (rank.name, rank.min_points, rank.gift)
        response = self.client.post(
            reverse('rating_admin:city_rank_gift_update', args=[rank.pk]),
            {'action': 'save', 'gift': 'Подарок Новосибирска'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            CityRankGift.objects.get(city=self.city_a, rank=rank).gift,
            'Подарок Новосибирска',
        )
        self.assertFalse(CityRankGift.objects.filter(city=self.city_b, rank=rank).exists())
        repeated = self.client.post(
            reverse('rating_admin:city_rank_gift_update', args=[rank.pk]),
            {'action': 'save', 'gift': 'Обновлённый подарок Новосибирска'},
        )
        self.assertEqual(repeated.status_code, 302)
        self.assertEqual(CityRankGift.objects.filter(city=self.city_a, rank=rank).count(), 1)
        self.assertEqual(
            CityRankGift.objects.get(city=self.city_a, rank=rank).gift,
            'Обновлённый подарок Новосибирска',
        )
        rank.refresh_from_db()
        self.assertEqual((rank.name, rank.min_points, rank.gift), original)

        self.assertEqual(
            self.client.post(
                reverse('rating_admin:catalog'),
                {'intro_title': 'Попытка изменить глобальный текст'},
            ).status_code,
            403,
        )

        self.assertEqual(
            self.client.get(reverse('rating_admin:format_edit', args=[rating_format.pk])).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse('rating_admin:rank_edit', args=[rank.pk])).status_code,
            403,
        )
        self.assertEqual(self.client.get(reverse('rating_admin:rank_create')).status_code, 403)
        self.assertEqual(self.client.get(reverse('rating_admin:integration_settings')).status_code, 403)

    def test_duplicate_team_requires_warning_confirmation_but_remains_allowed(self):
        self.client.force_login(self.operator)
        url = reverse('rating_admin:team_create')
        payload = {'name': self.own_team.name, 'phone': '+79995550000'}
        warning = self.client.post(url, payload)
        self.assertEqual(warning.status_code, 200)
        self.assertContains(warning, 'похожая команда')
        self.assertEqual(Team.objects.filter(city=self.city_a, normalized_name=self.own_team.normalized_name).count(), 1)
        payload['confirm_duplicate'] = 'on'
        confirmed = self.client.post(url, payload)
        self.assertEqual(confirmed.status_code, 302)
        self.assertEqual(Team.objects.filter(city=self.city_a, normalized_name=self.own_team.normalized_name).count(), 2)

    def test_similar_name_and_matching_phone_warn_but_unrelated_name_does_not(self):
        existing = team(
            self.operator,
            self.city_a,
            name='Команда Альфа',
            phone='+79995550101',
        )
        self.client.force_login(self.operator)
        url = reverse('rating_admin:team_create')

        unrelated = self.client.post(
            url,
            {'name': 'Сборная далёкой галактики', 'phone': '+79995550202'},
        )
        self.assertEqual(unrelated.status_code, 302)

        typo_payload = {'name': 'Команда Альфаа', 'phone': '+79995550303'}
        typo = self.client.post(url, typo_payload)
        self.assertEqual(typo.status_code, 200)
        self.assertContains(typo, 'похожая команда')
        self.assertFalse(
            Team.objects.filter(city=self.city_a, normalized_name='команда альфаа').exists()
        )

        phone_match = self.client.post(
            url,
            {'name': 'Другое название', 'phone': existing.phone},
        )
        self.assertEqual(phone_match.status_code, 200)
        self.assertContains(phone_match, 'похожая команда')

        typo_payload['confirm_duplicate'] = 'on'
        confirmed = self.client.post(url, typo_payload)
        self.assertEqual(confirmed.status_code, 302)
        self.assertTrue(
            Team.objects.filter(city=self.city_a, normalized_name='команда альфаа').exists()
        )

    def test_central_test_send_uses_saved_canonical_number_and_forces_test_mode(self):
        admin = user('test-send-admin', superuser=True)
        settings_url = reverse('rating_admin:integration_settings')
        send_url = reverse('rating_admin:integration_test_send')
        self.client.force_login(self.operator)
        self.assertEqual(self.client.post(send_url).status_code, 403)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(send_url).status_code, 405)
        saved = self.client.post(
            settings_url,
            {
                'sender_name': 'Quiz',
                'test_mode': 'on',
                'test_phone': '89991234567',
            },
        )
        self.assertEqual(
            saved.status_code,
            302,
            saved.context['integration_form'].errors.as_json() if saved.context else '',
        )
        integration = SmsIntegrationSettings.get_solo()
        self.assertEqual(integration.test_phone, '+79991234567')
        self.assertFalse(integration.emergency_stop)
        client = mock.Mock()
        client.send.return_value = ProviderResult(
            MessageDelivery.Status.ACCEPTED,
            provider_message_id='must-not-render-provider-id',
            provider_status_code='0',
        )
        with mock.patch('rating.views_admin.SmsPilotClient', return_value=client):
            response = self.client.post(send_url, follow=True)
        self.assertEqual(response.status_code, 200)
        client.send.assert_called_once()
        test_delivery = client.send.call_args.args[0]
        self.assertEqual(test_delivery.recipient, '+79991234567')
        self.assertEqual(
            test_delivery.rendered_body,
            'Тестовое сообщение рейтинга. Отправка в режиме test=1.',
        )
        self.assertTrue(client.send.call_args.kwargs['test_mode'])

    def test_central_test_send_obeys_emergency_stop_without_calling_provider(self):
        admin = user('stopped-test-send-admin', superuser=True)
        integration = SmsIntegrationSettings.get_solo()
        integration.test_phone = '+79991234567'
        integration.emergency_stop = True
        integration.save(update_fields=('test_phone', 'emergency_stop'))
        self.client.force_login(admin)
        client = mock.Mock()

        with mock.patch('rating.views_admin.SmsPilotClient', return_value=client):
            response = self.client.post(
                reverse('rating_admin:integration_test_send'),
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        client.send.assert_not_called()
        self.assertContains(response, 'аварийн')
        self.assertNotContains(response, 'must-not-render-provider-id')

    @override_settings(RATING_SECRET_ENCRYPTION_KEY='test-only-master')
    def test_integration_key_is_write_only_replace_preserve_clear_and_env_locked(self):
        admin = user('admin', superuser=True)
        self.client.force_login(admin)
        url = reverse('rating_admin:integration_settings')
        response = self.client.post(
            url,
            {
                'sender_name': 'Quiz', 'test_mode': 'on',
                'api_key': 'first-browser-secret',
            },
        )
        self.assertEqual(response.status_code, 302)
        settings = SmsIntegrationSettings.get_solo()
        first_ciphertext = settings.api_key_ciphertext
        self.assertNotIn('first-browser-secret', first_ciphertext)
        page = self.client.get(url)
        self.assertNotContains(page, 'first-browser-secret')
        self.assertNotContains(page, first_ciphertext)
        self.client.post(url, {'sender_name': 'Quiz', 'test_mode': 'on', 'api_key': ''})
        settings.refresh_from_db()
        self.assertEqual(settings.api_key_ciphertext, first_ciphertext)
        self.client.post(url, {'sender_name': 'Quiz', 'test_mode': 'on', 'clear_api_key': 'on'})
        settings.refresh_from_db()
        self.assertEqual(settings.api_key_ciphertext, '')
        settings.api_key_ciphertext = first_ciphertext
        settings.save(update_fields=('api_key_ciphertext',))
        with mock.patch.dict(os.environ, {'SMSPILOT_API_KEY': 'environment-secret'}):
            page = self.client.get(url)
            self.assertNotContains(page, 'environment-secret')
            self.assertContains(page, 'окружением')
            self.client.post(
                url,
                {'sender_name': 'Quiz', 'test_mode': 'on', 'api_key': 'replacement'},
            )
        settings.refresh_from_db()
        self.assertEqual(settings.api_key_ciphertext, first_ciphertext)

    def test_bulk_unknown_requires_preview_confirmation_and_commit_token(self):
        admin = user('admin', superuser=True)
        failed = delivery_for(score(self.own_team), status=MessageDelivery.Status.FAILED)
        unknown = delivery_for(score(self.own_team), status=MessageDelivery.Status.UNKNOWN)
        bulk_operation = operation_id()
        self.client.force_login(admin)
        preview_url = reverse('rating_admin:bulk_message_preview')
        response = self.client.post(
            preview_url,
            {
                'statuses': ['unknown'],
                'operation_id': bulk_operation,
                'reason': 'Проверка массового повтора',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['bulk_preview'])
        self.assertContains(response, 'Подтвердите риск unknown')
        response = self.client.post(
            preview_url,
            {
                'statuses': ['failed', 'unknown'],
                'confirm_unknown': 'on',
                'operation_id': bulk_operation,
                'reason': 'Проверка массового повтора',
            },
        )
        token = response.context['bulk_preview'].preview_token
        self.assertEqual(response.context['bulk_preview'].count, 2)
        commit = self.client.post(reverse('rating_admin:bulk_message_commit'), {'preview_token': token})
        self.assertEqual(commit.status_code, 302)
        failed.refresh_from_db()
        unknown.refresh_from_db()
        self.assertEqual((failed.status, unknown.status), ('queued', 'queued'))
        attempts = MessageAttempt.objects.filter(delivery__in=(failed, unknown)).order_by('delivery_id')
        self.assertEqual(attempts.count(), 2)
        self.assertEqual(set(attempts.values_list('actor_id', flat=True)), {admin.pk})
        self.assertEqual(
            set(attempts.values_list('reason', flat=True)), {'Проверка массового повтора'}
        )
        repeated = self.client.post(
            reverse('rating_admin:bulk_message_commit'), {'preview_token': token}
        )
        self.assertEqual(repeated.status_code, 409)
        self.assertEqual(MessageAttempt.objects.filter(delivery__in=(failed, unknown)).count(), 2)

    def test_bulk_retry_rolls_back_every_row_when_preview_state_drifts(self):
        admin = user('admin', superuser=True)
        first = delivery_for(score(self.own_team), status=MessageDelivery.Status.FAILED)
        second = delivery_for(score(self.own_team), status=MessageDelivery.Status.FAILED)
        self.client.force_login(admin)
        response = self.client.post(
            reverse('rating_admin:bulk_message_preview'),
            {
                'statuses': ['failed'],
                'operation_id': operation_id(),
                'reason': 'Атомарная проверка',
            },
        )
        token = response.context['bulk_preview'].preview_token
        MessageDelivery.objects.filter(pk=second.pk).update(status=MessageDelivery.Status.DELIVERED)
        commit = self.client.post(
            reverse('rating_admin:bulk_message_commit'), {'preview_token': token}
        )
        self.assertEqual(commit.status_code, 409)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.status, second.status), ('failed', 'delivered'))
        self.assertFalse(MessageAttempt.objects.filter(delivery__in=(first, second)).exists())

    def test_adjustment_reversal_has_linked_post_only_tenant_safe_workflow(self):
        adjustment, _ = apply_adjustment(
            actor=self.operator,
            team_score=score(self.own_team),
            delta_points='10',
            delta_games=1,
            reason='Ошибочная игра',
            source=ScoreAdjustment.Source.GAME_RESULT,
            operation_id=operation_id(),
            expected_version=0,
        )
        choices = dict(ScoreAdjustmentForm().fields['source'].choices)
        self.assertNotIn(ScoreAdjustment.Source.REVERSAL, choices)
        url = reverse('rating_admin:adjustment_reverse', args=[adjustment.pk])
        self.client.force_login(self.foreign_operator)
        self.assertEqual(self.client.post(url, {'operation_id': operation_id(), 'reason': 'Чужая'}).status_code, 404)
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get(url).status_code, 405)
        detail = self.client.get(reverse('rating_admin:team_detail', args=[self.own_team.pk]))
        self.assertContains(detail, url)
        reversal_operation = operation_id()
        response = self.client.post(
            url, {'operation_id': reversal_operation, 'reason': 'Исправление ошибки'}
        )
        self.assertEqual(response.status_code, 302)
        reversal = ScoreAdjustment.objects.get(reverses=adjustment)
        self.assertEqual(reversal.source, ScoreAdjustment.Source.REVERSAL)
        self.assertEqual(reversal.author_id, self.operator.pk)
        self.assertEqual(reversal.reason, 'Исправление ошибки')
        current = score(self.own_team)
        self.assertEqual((current.points, current.games), (0, 0))
        repeated = self.client.post(
            url, {'operation_id': reversal_operation, 'reason': 'Исправление ошибки'}
        )
        self.assertEqual(repeated.status_code, 302)
        self.assertEqual(ScoreAdjustment.objects.filter(reverses=adjustment).count(), 1)

    def test_event_history_filters_source_direction_and_preserves_query_in_pagination(self):
        own_score = score(self.own_team)
        for index in range(26):
            RankChangeEvent.objects.create(
                team_score=own_score,
                source=RankChangeEvent.Source.CATALOG,
                direction=RankChangeEvent.Direction.INCREASE,
                new_rank_level=1,
                new_rank_name='Каталог {}'.format(index),
            )
        RankChangeEvent.objects.create(
            team_score=own_score,
            source=RankChangeEvent.Source.ADJUSTMENT,
            direction=RankChangeEvent.Direction.DECREASE,
            old_rank_level=1,
            old_rank_name='Исправление',
        )
        self.client.force_login(self.operator)
        response = self.client.get(
            reverse('rating_admin:event_history'),
            {'format': 'classic', 'source': 'recalculation', 'direction': 'increase'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 26)
        self.assertContains(response, 'source=recalculation')
        self.assertContains(response, 'direction=increase')
        adjustment = self.client.get(
            reverse('rating_admin:event_history'),
            {'source': 'adjustment', 'direction': 'decrease'},
        )
        self.assertEqual(adjustment.context['page_obj'].paginator.count, 1)

    def test_new_rank_events_never_show_demotions_even_with_tampered_direction(self):
        own_score = score(self.own_team)
        RankChangeEvent.objects.create(
            team_score=own_score,
            source=RankChangeEvent.Source.ADJUSTMENT,
            direction=RankChangeEvent.Direction.INCREASE,
            new_rank_level=2,
            new_rank_name='Повышение видно',
        )
        RankChangeEvent.objects.create(
            team_score=own_score,
            source=RankChangeEvent.Source.ADJUSTMENT,
            direction=RankChangeEvent.Direction.DECREASE,
            old_rank_level=2,
            old_rank_name='Понижение скрыто',
        )
        self.client.force_login(self.operator)
        url = reverse('rating_admin:event_list')

        for supplied_direction in ('decrease', 'all'):
            with self.subTest(direction=supplied_direction):
                response = self.client.get(url, {'direction': supplied_direction})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['page_obj'].paginator.count, 1)
                self.assertContains(response, 'Повышение видно')
                self.assertNotContains(response, 'Понижение скрыто')
                self.assertNotContains(response, 'value="decrease"')
                self.assertNotContains(response, 'value="all"')

        history = self.client.get(
            reverse('rating_admin:event_history'),
            {'direction': 'decrease'},
        )
        self.assertContains(history, 'Понижение скрыто')

    def test_acknowledgement_is_shared_idempotent_tenant_safe_and_does_not_change_obligations(self):
        second_operator = user('second', city_obj=self.city_a)
        adjustment, _ = apply_adjustment(
            actor=self.operator,
            team_score=score(self.own_team),
            delta_points='2500',
            delta_games=1,
            reason='Игра',
            source=ScoreAdjustment.Source.GAME_RESULT,
            operation_id=operation_id(),
            expected_version=0,
        )
        event = RankChangeEvent.objects.get(source_adjustment=adjustment)
        delivery = MessageDelivery.objects.get(event=event)
        gift = TeamRankAchievement.objects.get(team_score=event.team_score, rank__level=4)
        delivery_before = delivery.status
        gift_before = gift.gift_status
        url = reverse('rating_admin:event_acknowledge', args=[event.pk])

        self.client.force_login(second_operator)
        response = self.client.post(url, {'operation_id': operation_id()})
        self.assertEqual(response.status_code, 302)
        event.refresh_from_db()
        acknowledged_at = event.acknowledged_at
        self.assertEqual(event.acknowledged_by_id, second_operator.pk)
        self.assertIsNotNone(acknowledged_at)

        self.client.force_login(self.operator)
        event_list = self.client.get(reverse('rating_admin:event_list'))
        self.assertNotContains(event_list, self.own_team.name)
        repeated = self.client.post(url, {'operation_id': operation_id()})
        self.assertEqual(repeated.status_code, 302)
        event.refresh_from_db()
        self.assertEqual(event.acknowledged_by_id, second_operator.pk)
        self.assertEqual(event.acknowledged_at, acknowledged_at)

        self.client.force_login(self.foreign_operator)
        self.assertEqual(self.client.post(url, {'operation_id': operation_id()}).status_code, 404)
        event.refresh_from_db()
        delivery.refresh_from_db()
        gift.refresh_from_db()
        self.assertEqual(event.acknowledged_by_id, second_operator.pk)
        self.assertEqual(delivery.status, delivery_before)
        self.assertEqual(gift.gift_status, gift_before)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '.localhost'])
class AdminTeamListMatrixTests(TestCase):
    def setUp(self):
        self.city = city('admin-sort')
        self.foreign_city = city('admin-foreign')
        self.operator = user('admin-sort-operator', city_obj=self.city)
        foreign_operator = user('admin-foreign-operator', city_obj=self.foreign_city)
        foreign = team(foreign_operator, self.foreign_city, name='Foreign Hidden')
        self.classic = score(foreign).rating_format
        rank1 = self.classic.ranks.get(level=1)
        rank2 = self.classic.ranks.get(level=2)
        rows = (
            ('Alpha', 'Ирина Особая', '+79990000001', Decimal('100.0'), 4, None),
            ('Bravo', 'Борис', '+79990000002', Decimal('200.0'), 2, rank1),
            ('Charlie', 'Светлана', '+79990000003', Decimal('200.0'), 3, rank2),
            ('Delta', 'Дмитрий', '+79990000004', Decimal('50.0'), 3, rank2),
        )
        for name, captain, phone, points, games, current_rank in rows:
            item = team(
                self.operator,
                self.city,
                name=name,
                captain_name=captain,
                phone=phone,
            )
            item_score = score(item)
            item_score.points = points
            item_score.games = games
            item_score.current_rank = current_rank
            item_score.save(update_fields=('points', 'games', 'current_rank'))
        self.client.force_login(self.operator)

    def test_scoped_search_matches_name_captain_and_phone(self):
        url = reverse('rating_admin:team_list')
        for query, expected in (
            ('Alpha', 'Alpha'),
            ('Особая', 'Alpha'),
            ('79990000003', 'Charlie'),
        ):
            with self.subTest(query=query):
                response = self.client.get(url, {'q': query, 'format': 'classic'})
                self.assertEqual(
                    [row.name for row in response.context['page_obj'].object_list],
                    [expected],
                )
                self.assertNotContains(response, 'Foreign Hidden')

    def test_four_admin_sorts_both_directions_have_stable_name_ties(self):
        expected = {
            ('points', 'asc'): ['Delta', 'Alpha', 'Bravo', 'Charlie'],
            ('points', 'desc'): ['Bravo', 'Charlie', 'Alpha', 'Delta'],
            ('rank', 'asc'): ['Alpha', 'Bravo', 'Charlie', 'Delta'],
            ('rank', 'desc'): ['Charlie', 'Delta', 'Bravo', 'Alpha'],
            ('name', 'asc'): ['Alpha', 'Bravo', 'Charlie', 'Delta'],
            ('name', 'desc'): ['Delta', 'Charlie', 'Bravo', 'Alpha'],
            ('games', 'asc'): ['Bravo', 'Charlie', 'Delta', 'Alpha'],
            ('games', 'desc'): ['Alpha', 'Charlie', 'Delta', 'Bravo'],
        }
        for (sort, direction), names in expected.items():
            with self.subTest(sort=sort, direction=direction):
                response = self.client.get(
                    reverse('rating_admin:team_list'),
                    {'format': 'classic', 'sort': sort, 'direction': direction},
                )
                self.assertEqual(
                    [row.name for row in response.context['page_obj'].object_list], names
                )

    def test_pagination_fetches_only_the_requested_page_and_keeps_stable_boundaries(self):
        for index in range(51):
            team(self.operator, self.city, name='Paged Team {:03d}'.format(index))
        url = reverse('rating_admin:team_list')
        params = {'format': 'classic', 'sort': 'name', 'direction': 'asc'}

        with CaptureQueriesContext(connection) as captured:
            second = self.client.get(url, dict(params, page=2))
        self.assertEqual(second.status_code, 200)
        self.assertEqual(len(second.context['page_obj'].object_list), 25)
        row_queries = [
            item['sql']
            for item in captured.captured_queries
            if 'SELECT "rating_team"."id"' in item['sql']
        ]
        self.assertTrue(row_queries, [item['sql'] for item in captured.captured_queries])
        self.assertTrue(any('LIMIT 25 OFFSET 25' in sql for sql in row_queries), row_queries)
        self.assertTrue(all('LIMIT 25' in sql for sql in row_queries), row_queries)

        pages = [
            self.client.get(url, dict(params, page=page)).context['page_obj']
            for page in (1, 2, 3)
        ]
        names = [row.name for page in pages for row in page.object_list]
        self.assertEqual(len(names), pages[0].paginator.count)
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names, sorted(names, key=str.casefold))
