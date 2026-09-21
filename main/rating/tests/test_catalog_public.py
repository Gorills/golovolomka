import io
from decimal import Decimal
from unittest import mock

from PIL import Image

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from home.sitemaps import CityRatingSitemap
from rating.models import (
    CityRankGift,
    MessageDelivery,
    RankChangeEvent,
    RatingFormat,
    RatingPageSettings,
    ScoreAdjustment,
    TeamRankAchievement,
)
from rating.forms import RankForm, RatingPageSettingsForm
from rating.uploads import MAX_LOGO_BYTES, rank_logo_path
from rating.services import (
    ConcurrencyConflict,
    StalePreview,
    ValidationError,
    build_rank_preview,
    commit_rank_preview,
    apply_adjustment,
)

from .factories import city, operation_id, score, team, user


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '.localhost'])
class CatalogAndPublicTests(TestCase):
    def setUp(self):
        self.city_a = city('nsk')
        self.city_b = city('tomsk')
        self.admin = user('admin', superuser=True)
        self.team_a = team(self.admin, self.city_a, name='<script>alert(1)</script>')
        self.team_b = team(self.admin, self.city_b, name='Секретная команда')
        self.score_a = score(self.team_a)
        self.score_b = score(self.team_b)
        self.classic = RatingFormat.objects.get(code='classic')

    def select_admin_city(self):
        response = self.client.post(
            reverse('rating_admin:city_select'), {'city': self.city_a.slug}
        )
        self.assertEqual(response.status_code, 302)

    def rank_edit_payload(self, rank, *, min_points=None, is_active=None, name=None):
        payload = {
            'rating_format': rank.rating_format_id,
            'level': rank.level,
            'min_points': rank.min_points if min_points is None else min_points,
            'name': rank.name if name is None else name,
            'logo_alt': rank.logo_alt,
            'description': rank.description,
            'gift': rank.gift,
        }
        if rank.is_active if is_active is None else is_active:
            payload['is_active'] = 'on'
        return payload

    def test_http_threshold_change_requires_preview_then_commits_atomically_and_rejects_stale(self):
        self.client.force_login(self.admin)
        rank = self.classic.ranks.get(level=1)
        self.score_a.points = Decimal('250.0')
        self.score_a.save(update_fields=('points',))
        self.team_a.name = 'Команда предпросмотра'
        self.team_a.normalized_name = 'команда предпросмотра'
        self.team_a.save(update_fields=('name', 'normalized_name'))
        edit_url = reverse('rating_admin:rank_edit', args=[rank.pk])

        preview_response = self.client.post(
            edit_url, self.rank_edit_payload(rank, min_points=200)
        )
        self.assertEqual(preview_response.status_code, 200)
        preview = preview_response.context['rank_preview']
        self.assertIsNotNone(preview)
        self.assertEqual(preview['affected_count'], 1)
        self.assertContains(preview_response, self.city_a.name)
        self.assertContains(preview_response, self.team_a.name)
        self.assertContains(preview_response, 'Без ранга')
        self.assertContains(preview_response, rank.name)
        rank.refresh_from_db()
        self.score_a.refresh_from_db()
        self.assertEqual(rank.min_points, 300)
        self.assertIsNone(self.score_a.current_rank_id)
        self.assertFalse(RankChangeEvent.objects.filter(source=RankChangeEvent.Source.CATALOG).exists())

        commit_response = self.client.post(
            reverse('rating_admin:rank_change_commit', args=[rank.pk]),
            {'preview_token': preview['preview_token']},
        )
        self.assertRedirects(
            commit_response, reverse('rating_admin:catalog'), fetch_redirect_response=False
        )
        rank.refresh_from_db()
        self.score_a.refresh_from_db()
        self.assertEqual(rank.min_points, 200)
        self.assertEqual(self.score_a.current_rank_id, rank.pk)
        self.assertEqual(
            RankChangeEvent.objects.filter(
                team_score=self.score_a, source=RankChangeEvent.Source.CATALOG
            ).count(),
            1,
        )
        self.assertFalse(TeamRankAchievement.objects.filter(team_score=self.score_a).exists())
        self.assertFalse(MessageDelivery.objects.filter(event__team_score=self.score_a).exists())

        stale_preview_response = self.client.post(
            edit_url, self.rank_edit_payload(rank, min_points=150)
        )
        self.assertEqual(stale_preview_response.status_code, 200)
        stale_token = stale_preview_response.context['rank_preview']['preview_token']
        self.score_a.version += 1
        self.score_a.save(update_fields=('version',))
        stale_commit = self.client.post(
            reverse('rating_admin:rank_change_commit', args=[rank.pk]),
            {'preview_token': stale_token},
        )
        self.assertEqual(stale_commit.status_code, 409)
        rank.refresh_from_db()
        self.assertEqual(rank.min_points, 200)
        self.assertEqual(
            RankChangeEvent.objects.filter(
                team_score=self.score_a, source=RankChangeEvent.Source.CATALOG
            ).count(),
            1,
        )

    def test_http_rank_deactivation_requires_preview_and_recalculates_without_side_effects(self):
        self.client.force_login(self.admin)
        rank = self.classic.ranks.get(level=1)
        self.score_a.points = Decimal('350.0')
        self.score_a.current_rank = rank
        self.score_a.save(update_fields=('points', 'current_rank'))
        edit_url = reverse('rating_admin:rank_edit', args=[rank.pk])

        preview_response = self.client.post(
            edit_url, self.rank_edit_payload(rank, is_active=False)
        )
        self.assertEqual(preview_response.status_code, 200)
        preview = preview_response.context['rank_preview']
        self.assertIsNotNone(preview)
        self.assertEqual(preview['affected_count'], 1)
        rank.refresh_from_db()
        self.assertTrue(rank.is_active)
        self.score_a.refresh_from_db()
        self.assertEqual(self.score_a.current_rank_id, rank.pk)

        response = self.client.post(
            reverse('rating_admin:rank_change_commit', args=[rank.pk]),
            {'preview_token': preview['preview_token']},
        )
        self.assertEqual(response.status_code, 302)
        rank.refresh_from_db()
        self.score_a.refresh_from_db()
        self.assertFalse(rank.is_active)
        self.assertIsNone(self.score_a.current_rank_id)
        event = RankChangeEvent.objects.get(
            team_score=self.score_a, source=RankChangeEvent.Source.CATALOG
        )
        self.assertEqual(event.direction, RankChangeEvent.Direction.DECREASE)
        self.assertFalse(TeamRankAchievement.objects.filter(team_score=self.score_a).exists())
        self.assertFalse(MessageDelivery.objects.filter(event=event).exists())

    def test_existing_rank_level_is_immutable_and_invalid_edit_preserves_catalog_and_ledger(self):
        self.client.force_login(self.admin)
        rank = self.classic.ranks.get(level=1)
        original = (rank.level, rank.min_points, self.classic.catalog_version)
        payload = self.rank_edit_payload(rank, name='Попытка перестановки')
        payload['level'] = 13
        response = self.client.post(
            reverse('rating_admin:rank_edit', args=[rank.pk]),
            payload,
        )
        self.assertEqual(response.status_code, 302)
        rank.refresh_from_db()
        self.classic.refresh_from_db()
        self.assertEqual((rank.level, rank.min_points), original[:2])
        self.assertEqual(rank.name, 'Попытка перестановки')
        self.assertEqual(self.classic.catalog_version, original[2] + 1)
        self.assertFalse(RankChangeEvent.objects.exists())
        self.assertFalse(TeamRankAchievement.objects.exists())
        self.assertFalse(MessageDelivery.objects.exists())

    def test_adjustment_http_preview_renders_old_and_new_rank_names(self):
        self.client.force_login(self.admin)
        self.select_admin_city()
        rank = self.classic.ranks.get(level=1)
        response = self.client.post(
            reverse('rating_admin:score_adjust', args=[self.team_a.pk, 'classic']),
            {
                'operation_id': operation_id(),
                'delta_points': '300',
                'delta_games': 1,
                'reason': 'Игра',
                'source': ScoreAdjustment.Source.GAME_RESULT,
                'expected_version': 0,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Без ранга → {}'.format(rank.name))
        self.score_a.refresh_from_db()
        self.assertEqual((self.score_a.points, self.score_a.version), (Decimal('0.0'), 0))

    def test_public_gifts_are_city_specific_and_fall_back_per_rank(self):
        rank = self.classic.ranks.get(level=1)
        rank.gift = 'Глобальный подарок'
        rank.save(update_fields=('gift',))

        fallback = self.client.get('/rating/?format=classic', HTTP_HOST='nsk.localhost')
        self.assertContains(fallback, 'Глобальный подарок')

        CityRankGift.objects.create(
            city=self.city_a,
            rank=rank,
            gift='Подарок Новосибирска',
            updated_by=self.admin,
        )
        CityRankGift.objects.create(
            city=self.city_b,
            rank=rank,
            gift='Подарок Томска',
            updated_by=self.admin,
        )
        city_a_page = self.client.get('/rating/?format=classic', HTTP_HOST='nsk.localhost')
        city_b_page = self.client.get('/rating/?format=classic', HTTP_HOST='tomsk.localhost')
        self.assertContains(city_a_page, 'Подарок Новосибирска')
        self.assertNotContains(city_a_page, 'Подарок Томска')
        self.assertContains(city_b_page, 'Подарок Томска')
        self.assertNotContains(city_b_page, 'Подарок Новосибирска')

        CityRankGift.objects.filter(city=self.city_a, rank=rank).update(gift='')
        disabled = self.client.get('/rating/?format=classic', HTTP_HOST='nsk.localhost')
        self.assertNotContains(disabled, 'Глобальный подарок')

        CityRankGift.objects.filter(city=self.city_a, rank=rank).delete()
        restored = self.client.get('/rating/?format=classic', HTTP_HOST='nsk.localhost')
        self.assertContains(restored, 'Глобальный подарок')

    def test_achievement_snapshots_city_gift_instead_of_global_default(self):
        rank = self.classic.ranks.get(level=1)
        rank.gift = 'Глобальный подарок'
        rank.save(update_fields=('gift',))
        CityRankGift.objects.create(
            city=self.city_a,
            rank=rank,
            gift='Городской подарок',
            updated_by=self.admin,
        )

        apply_adjustment(
            actor=self.admin,
            team_score=self.score_a,
            delta_points=rank.min_points,
            delta_games=1,
            reason='Игра в Новосибирске',
            source=ScoreAdjustment.Source.GAME_RESULT,
            operation_id=operation_id(),
            expected_version=0,
        )
        achievement = TeamRankAchievement.objects.get(team_score=self.score_a, rank=rank)
        self.assertEqual(achievement.gift_snapshot, 'Городской подарок')
        self.assertEqual(achievement.gift_status, TeamRankAchievement.GiftStatus.PENDING)

    def test_stale_adjustment_commit_shows_fresh_score_and_preserves_proposed_input(self):
        self.client.force_login(self.admin)
        self.select_admin_city()
        proposed_operation = operation_id()
        preview_response = self.client.post(
            reverse('rating_admin:score_adjust', args=[self.team_a.pk, 'classic']),
            {
                'operation_id': proposed_operation,
                'delta_points': '300',
                'delta_games': 1,
                'reason': 'Предложенная игра',
                'source': ScoreAdjustment.Source.GAME_RESULT,
                'expected_version': 0,
            },
        )
        token = preview_response.context['preview'].preview_token
        apply_adjustment(
            actor=self.admin,
            team_score=self.score_a,
            delta_points='50',
            delta_games=0,
            reason='Параллельная правка',
            source=ScoreAdjustment.Source.CORRECTION,
            operation_id=operation_id(),
            expected_version=0,
        )
        response = self.client.post(
            reverse('rating_admin:score_adjust_commit', args=[self.team_a.pk, 'classic']),
            {'preview_token': token},
        )
        self.assertEqual(response.status_code, 409)
        self.assertTrue(response.context['is_stale'])
        self.assertEqual(response.context['score'].points, Decimal('50.0'))
        self.assertEqual(response.context['score'].version, 1)
        form = response.context['form']
        self.assertEqual(str(form['operation_id'].value()), str(proposed_operation))
        self.assertEqual(form['delta_points'].value(), '300.0')
        self.assertEqual(form['delta_games'].value(), 1)
        self.assertEqual(form['reason'].value(), 'Предложенная игра')
        self.assertEqual(form['expected_version'].value(), 1)

    def test_reactivating_format_backfills_only_missing_zero_scores(self):
        self.client.force_login(self.admin)
        fans = RatingFormat.objects.get(code='fans')
        fans.is_active = False
        fans.save(update_fields=('is_active',))
        late_team = team(self.admin, self.city_a, name='Команда неактивного формата')
        self.assertTrue(late_team.scores.filter(rating_format=fans).exists())
        self.assertEqual(late_team.scores.count(), RatingFormat.objects.count())
        self.team_a.scores.filter(rating_format=fans).delete()
        response = self.client.post(
            reverse('rating_admin:format_edit', args=[fans.pk]),
            {
                'name': fans.name,
                'description': fans.description,
                'order': fans.order,
                'is_active': 'on',
            },
        )
        self.assertEqual(response.status_code, 302)
        restored = self.team_a.scores.get(rating_format=fans)
        self.assertEqual(
            (restored.points, restored.games, restored.current_rank_id, restored.version),
            (Decimal('0.0'), 0, None, 0),
        )
        self.assertFalse(RankChangeEvent.objects.exists())
        self.assertFalse(TeamRankAchievement.objects.exists())
        self.assertFalse(MessageDelivery.objects.exists())

    def test_sms_template_rejects_format_specs_before_save(self):
        settings = RatingPageSettings.get_solo()
        form = RatingPageSettingsForm(
            {
                'intro_title': settings.intro_title,
                'intro_text': settings.intro_text,
                'gifts_title': settings.gifts_title,
                'gifts_text': settings.gifts_text,
                'seo_title': settings.seo_title,
                'seo_description': settings.seo_description,
                'sms_template': '{team:bad} {rating_url}',
            },
            instance=settings,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('sms_template', form.errors)

    def test_threshold_decrease_preview_uses_proposed_value(self):
        rank = self.classic.ranks.get(level=1)
        self.score_a.points = Decimal('250.0')
        self.score_a.save(update_fields=('points',))
        preview = build_rank_preview(
            actor=self.admin,
            rank=rank,
            proposed={
                'min_points': 200, 'name': rank.name, 'description': rank.description,
                'gift': rank.gift, 'is_active': True,
            },
        )
        self.assertEqual(preview['affected_count'], 1)
        self.assertEqual(preview['affected_rows'][0]['team_name'], self.team_a.name)
        self.assertEqual(preview['affected_rows'][0]['new_rank_name'], rank.name)

    def test_stale_catalog_preview_changes_nothing(self):
        rank = self.classic.ranks.get(level=1)
        original = rank.min_points
        preview = build_rank_preview(
            actor=self.admin,
            rank=rank,
            proposed={'min_points': 200, 'name': rank.name, 'is_active': True},
        )
        self.score_a.points = Decimal('1.0')
        self.score_a.version += 1
        self.score_a.save(update_fields=('points', 'version'))
        with self.assertRaises(StalePreview):
            commit_rank_preview(actor=self.admin, token=preview['preview_token'])
        rank.refresh_from_db()
        self.assertEqual(rank.min_points, original)
        self.assertFalse(RankChangeEvent.objects.filter(source=RankChangeEvent.Source.CATALOG).exists())

    def test_catalog_cas_zero_rolls_back_rank_event_and_score(self):
        rank = self.classic.ranks.get(level=1)
        self.score_a.points = Decimal('250.0')
        self.score_a.save(update_fields=('points',))
        preview = build_rank_preview(
            actor=self.admin,
            rank=rank,
            proposed={'min_points': 200, 'name': rank.name, 'is_active': True},
        )
        with mock.patch('django.db.models.query.QuerySet.update', return_value=0):
            with self.assertRaises(ConcurrencyConflict):
                commit_rank_preview(actor=self.admin, token=preview['preview_token'])
        rank.refresh_from_db()
        self.score_a.refresh_from_db()
        self.assertEqual(rank.min_points, 300)
        self.assertIsNone(self.score_a.current_rank_id)
        self.assertFalse(RankChangeEvent.objects.filter(source=RankChangeEvent.Source.CATALOG).exists())
        self.assertFalse(TeamRankAchievement.objects.filter(team_score=self.score_a).exists())
        self.assertFalse(MessageDelivery.objects.filter(event__team_score=self.score_a).exists())

    def test_invalid_threshold_order_rolls_back_rank_and_recalculation(self):
        rank = self.classic.ranks.get(level=2)
        original = rank.min_points
        preview = build_rank_preview(
            actor=self.admin,
            rank=rank,
            proposed={'min_points': 100, 'name': rank.name, 'is_active': True},
        )
        with self.assertRaises(ValidationError):
            commit_rank_preview(actor=self.admin, token=preview['preview_token'])
        rank.refresh_from_db()
        self.assertEqual(rank.min_points, original)
        self.assertFalse(RankChangeEvent.objects.filter(source=RankChangeEvent.Source.CATALOG).exists())

    def test_catalog_recalculation_creates_event_but_no_gift_or_sms(self):
        rank = self.classic.ranks.get(level=1)
        self.score_a.points = Decimal('250.0')
        self.score_a.save(update_fields=('points',))
        preview = build_rank_preview(
            actor=self.admin,
            rank=rank,
            proposed={
                'min_points': 200, 'name': rank.name, 'description': rank.description,
                'gift': rank.gift, 'is_active': True,
            },
        )
        commit_rank_preview(actor=self.admin, token=preview['preview_token'])
        self.score_a.refresh_from_db()
        self.assertEqual(self.score_a.current_rank_id, rank.pk)
        self.assertTrue(
            RankChangeEvent.objects.filter(
                team_score=self.score_a, source=RankChangeEvent.Source.CATALOG
            ).exists()
        )
        self.assertFalse(TeamRankAchievement.objects.filter(team_score=self.score_a).exists())
        self.assertFalse(MessageDelivery.objects.filter(event__team_score=self.score_a).exists())

    def test_public_page_is_tenant_scoped_escapes_content_and_hides_pii(self):
        self.team_a.phone = '+79991234567'
        self.team_a.captain_name = 'Очень секретный капитан'
        self.team_a.private_note = 'Закрытая заметка'
        self.team_a.save(update_fields=('phone', 'captain_name', 'private_note'))
        settings = RatingPageSettings.get_solo()
        settings.intro_title = '<b>Наш рейтинг</b>'
        settings.intro_text = '<script>bad()</script>'
        settings.seo_title = 'SEO рейтинга'
        settings.seo_description = 'Описание рейтинга'
        settings.save()
        response = self.client.get('/rating/', HTTP_HOST='nsk.localhost')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;', html=False)
        self.assertNotContains(response, '<script>alert(1)</script>', html=False)
        self.assertNotContains(response, 'Секретная команда')
        self.assertNotContains(response, '79991234567')
        self.assertNotContains(response, 'Очень секретный капитан')
        self.assertNotContains(response, 'Закрытая заметка')
        self.assertContains(response, 'SEO рейтинга')
        self.assertContains(response, '&lt;script&gt;bad()&lt;/script&gt;', html=False)

    def test_public_empty_city_and_all_format_gift_navigation(self):
        empty = city('empty')
        response = self.client.get('/rating/', HTTP_HOST='empty.localhost')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Рейтинг скоро начнётся')
        for name in ('Классика', 'Музыкалити', 'Фанаты'):
            self.assertContains(response, name)
        self.assertEqual(response.context['page_obj'].paginator.count, 0)

    def test_public_preloads_gifts_for_local_format_switching(self):
        musicality = RatingFormat.objects.get(code='musicality')
        classic_rank = self.classic.ranks.get(level=1)
        musicality_rank = musicality.ranks.get(level=1)
        classic_rank.gift = 'Подарок классики'
        classic_rank.save(update_fields=('gift',))
        musicality_rank.gift = 'Подарок музыкального формата'
        musicality_rank.save(update_fields=('gift',))

        response = self.client.get('/rating/?format=classic', HTTP_HOST='nsk.localhost')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Подарок классики')
        self.assertContains(response, 'Подарок музыкального формата')
        self.assertContains(response, 'data-gift-format="musicality"', html=False)
        self.assertContains(
            response,
            'data-gift-panel="musicality" hidden',
            html=False,
        )

    def test_public_h1_and_meta_description_are_city_specific(self):
        response = self.client.get('/rating/', HTTP_HOST='nsk.localhost')
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, '<h1 class="rating-title">Рейтинг команд — NSK</h1>', html=False
        )
        self.assertContains(
            response,
            '<meta name="description" content="Рейтинг команд — NSK">',
            html=False,
        )
        self.assertContains(response, '<title> Рейтинг команд — NSK</title>', html=False)
        self.assertNotContains(response, 'NSK — NSK')

    def test_public_filters_sort_and_pagination_are_server_side(self):
        for index in range(30):
            team(self.admin, self.city_a, name='Команда {:02d}'.format(index))
        response = self.client.get(
            '/rating/?format=classic&q=Команда&sort=name&direction=asc&page=2&secret=drop-me',
            HTTP_HOST='nsk.localhost',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertLessEqual(len(response.context['page_obj'].object_list), 25)
        self.assertEqual(response.context['canonical_url'], 'http://nsk.localhost/rating/')
        self.assertContains(response, '<link rel="canonical" href="http://nsk.localhost/rating/">', html=False)
        self.assertContains(
            response,
            '?format=classic&amp;q=%D0%9A%D0%BE%D0%BC%D0%B0%D0%BD%D0%B4%D0%B0&amp;sort=name&amp;direction=asc&amp;page=1',
            html=False,
        )
        self.assertNotContains(response, 'secret=drop-me')

    def test_rank_logo_rejects_non_image_oversize_and_missing_alt(self):
        rank = self.classic.ranks.get(level=1)
        common = {
            'rating_format': self.classic.pk,
            'level': rank.level,
            'min_points': rank.min_points,
            'name': rank.name,
            'description': rank.description,
            'gift': rank.gift,
            'is_active': 'on',
        }
        invalid = RankForm(
            common,
            {'logo': SimpleUploadedFile('attack.png', b'<script>alert(1)</script>', 'image/png')},
            instance=rank,
            lock_format=True,
        )
        self.assertFalse(invalid.is_valid())
        oversized = RankForm(
            dict(common, logo_alt='Логотип'),
            {'logo': SimpleUploadedFile('large.png', b'x' * (MAX_LOGO_BYTES + 1), 'image/png')},
            instance=rank,
            lock_format=True,
        )
        self.assertFalse(oversized.is_valid())
        buffer = io.BytesIO()
        Image.new('RGB', (2, 2), color='red').save(buffer, format='PNG')
        missing_alt = RankForm(
            common,
            {'logo': SimpleUploadedFile('valid.png', buffer.getvalue(), 'image/png')},
            instance=rank,
            lock_format=True,
        )
        self.assertFalse(missing_alt.is_valid())
        self.assertIn('logo_alt', missing_alt.errors)

    def test_rank_logo_storage_name_is_randomized_and_keeps_safe_extension(self):
        first = rank_logo_path(None, '../../same-name.png')
        second = rank_logo_path(None, '../../same-name.png')
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith('rating/ranks/'))
        self.assertTrue(first.endswith('.png'))
        self.assertNotIn('same-name', first)
        self.assertTrue(rank_logo_path(None, 'attack.svg').endswith('.img'))

    def test_allowed_logo_formats_and_max_dimension_are_accepted_with_alt(self):
        cases = (('PNG', 'logo.png', (2048, 1)), ('JPEG', 'logo.jpg', (2, 2)), ('WEBP', 'logo.webp', (2, 2)))
        for image_format, filename, dimensions in cases:
            with self.subTest(image_format=image_format):
                rank = self.classic.ranks.get(level=1)
                buffer = io.BytesIO()
                Image.new('RGB', dimensions, color='blue').save(buffer, format=image_format)
                form = RankForm(
                    {
                        'rating_format': self.classic.pk,
                        'level': rank.level,
                        'min_points': rank.min_points,
                        'name': rank.name,
                        'logo_alt': 'Логотип ранга',
                        'description': rank.description,
                        'gift': rank.gift,
                        'is_active': 'on',
                    },
                    {'logo': SimpleUploadedFile(filename, buffer.getvalue(), 'image/{}'.format(image_format.lower()))},
                    instance=rank,
                    lock_format=True,
                )
                self.assertTrue(form.is_valid(), form.errors.as_json())

    @override_settings(RATING_PUBLIC_URL_TEMPLATE='https://{city}.example.test/rating/')
    def test_sitemap_contains_absolute_rating_url_for_each_city(self):
        locations = [row['location'] for row in CityRatingSitemap().get_urls()]
        self.assertEqual(
            locations,
            ['https://nsk.example.test/rating/', 'https://tomsk.example.test/rating/'],
        )
        response = self.client.get('/sitemap.xml', HTTP_HOST='localhost')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'https://nsk.example.test/rating/')
        self.assertContains(response, 'https://tomsk.example.test/rating/')

    def test_rank_create_accepts_new_level_and_rejects_duplicate_or_non_strict_order_atomically(self):
        self.client.force_login(self.admin)
        url = reverse('rating_admin:rank_create')

        def payload(level, min_points, name):
            return {
                'rating_format': self.classic.pk,
                'level': level,
                'min_points': min_points,
                'name': name,
                'logo_alt': '',
                'description': '',
                'gift': '',
                'is_active': 'on',
            }

        before = self.classic.ranks.count()
        created = self.client.post(url, payload(13, 11000, 'Новый ранг'))
        self.assertRedirects(created, reverse('rating_admin:catalog'), fetch_redirect_response=False)
        self.assertTrue(self.classic.ranks.filter(level=13, min_points=11000, name='Новый ранг').exists())
        self.assertEqual(self.classic.ranks.count(), before + 1)

        duplicate = self.client.post(url, payload(13, 12000, 'Дубликат уровня'))
        self.assertEqual(duplicate.status_code, 200)
        self.assertContains(duplicate, 'уже существует')
        self.assertEqual(self.classic.ranks.count(), before + 1)

        non_strict = self.client.post(url, payload(14, 10500, 'Неверный порядок'))
        self.assertEqual(non_strict.status_code, 200)
        self.assertContains(non_strict, 'Пороги должны строго возрастать')
        self.assertFalse(self.classic.ranks.filter(level=14).exists())
        self.assertEqual(self.classic.ranks.count(), before + 1)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '.localhost'])
class PublicSortingMatrixTests(TestCase):
    def setUp(self):
        self.city = city('sort-city')
        self.admin = user('sort-admin', superuser=True)
        self.classic = RatingFormat.objects.get(code='classic')
        rank1 = self.classic.ranks.get(level=1)
        rank2 = self.classic.ranks.get(level=2)
        rows = (
            ('Alpha', Decimal('100.0'), 4, None),
            ('Bravo', Decimal('200.0'), 2, rank1),
            ('Charlie', Decimal('200.0'), 3, rank2),
            ('Delta', Decimal('50.0'), 3, rank2),
        )
        for name, points, games, current_rank in rows:
            item = team(self.admin, self.city, name=name)
            item_score = score(item)
            item_score.points = points
            item_score.games = games
            item_score.current_rank = current_rank
            item_score.save(update_fields=('points', 'games', 'current_rank'))

    def test_four_sorts_both_directions_have_stable_name_ties(self):
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
                    '/rating/',
                    {'format': 'classic', 'sort': sort, 'direction': direction},
                    HTTP_HOST='sort-city.localhost',
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    [row.team_name for row in response.context['page_obj'].object_list],
                    names,
                )
