import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.utils import timezone

from rating.models import (
    MessageDelivery,
    Rank,
    RankChangeEvent,
    RatingFormat,
    RatingPageSettings,
    ScoreAdjustment,
    Team,
    TeamRankAchievement,
    TeamScore,
)
from rating.services import (
    ConcurrencyConflict,
    IdempotencyConflict,
    ValidationError,
    apply_adjustment,
    parse_points,
    rank_for_points,
    reverse_adjustment,
    update_team,
)
from rating.seed import seed_catalog

from .factories import city, operation_id, score, team, user


class SeedContractTests(TestCase):
    def test_seed_is_idempotent_and_never_creates_teams(self):
        self.assertEqual((RatingFormat.objects.count(), Rank.objects.count(), Team.objects.count()), (3, 36, 0))
        seed_catalog(RatingFormat, Rank)
        self.assertEqual((RatingFormat.objects.count(), Rank.objects.count(), Team.objects.count()), (3, 36, 0))

    def test_repeated_seed_preserves_edited_catalog_and_existing_rating_state(self):
        city_obj = city('seed-city')
        actor = user('seed-operator', city_obj=city_obj)
        team_obj = team(
            actor,
            city_obj,
            phone='+79990000000',
            sms_allowed=True,
            consent_source='registration',
            consent_recorded_at='2026-09-17T12:00:00Z',
        )
        score_obj = score(team_obj)
        apply_adjustment(
            actor=actor,
            team_score=score_obj,
            delta_points='2500',
            delta_games=1,
            reason='Игра',
            source=ScoreAdjustment.Source.GAME_RESULT,
            operation_id=operation_id(),
            expected_version=0,
        )
        rating_format = RatingFormat.objects.get(code='classic')
        rating_format.name = 'Своя классика'
        rating_format.description = 'Редакторское описание'
        rating_format.order = 9
        rating_format.is_active = False
        rating_format.save()
        edited_rank = rating_format.ranks.get(level=4)
        edited_rank.min_points = 2100
        edited_rank.name = 'Собственный ранг'
        edited_rank.description = 'Собственное описание ранга'
        edited_rank.gift = 'Собственный подарок'
        edited_rank.is_active = False
        edited_rank.save()
        custom_rank = Rank.objects.create(
            rating_format=rating_format,
            level=13,
            min_points=11000,
            name='Дополнительный ранг',
            description='Добавлен через админку',
            gift='Дополнительный подарок',
            is_active=True,
        )
        musicality = RatingFormat.objects.get(code='musicality')
        musicality.ranks.get(level=12).delete()
        collision_rank = Rank.objects.create(
            rating_format=musicality,
            level=13,
            min_points=10000,
            name='Пользовательский коллизионный ранг',
        )
        score_obj.refresh_from_db()
        state_before = (
            score_obj.points,
            score_obj.games,
            score_obj.current_rank_id,
            score_obj.version,
            ScoreAdjustment.objects.count(),
            RankChangeEvent.objects.count(),
            TeamRankAchievement.objects.count(),
            MessageDelivery.objects.count(),
        )

        result = seed_catalog(RatingFormat, Rank)

        rating_format.refresh_from_db()
        edited_rank.refresh_from_db()
        custom_rank.refresh_from_db()
        score_obj.refresh_from_db()
        self.assertEqual(
            (rating_format.name, rating_format.description, rating_format.order, rating_format.is_active),
            ('Своя классика', 'Редакторское описание', 9, False),
        )
        self.assertEqual(
            (
                edited_rank.min_points,
                edited_rank.name,
                edited_rank.description,
                edited_rank.gift,
                edited_rank.is_active,
            ),
            (2100, 'Собственный ранг', 'Собственное описание ранга', 'Собственный подарок', False),
        )
        self.assertEqual(custom_rank.name, 'Дополнительный ранг')
        collision_rank.refresh_from_db()
        self.assertEqual(collision_rank.name, 'Пользовательский коллизионный ранг')
        self.assertFalse(musicality.ranks.filter(level=12).exists())
        self.assertIn(
            {'format_code': 'musicality', 'level': 12, 'min_points': 10000},
            result['skipped_rank_conflicts'],
        )
        self.assertEqual(
            (
                score_obj.points,
                score_obj.games,
                score_obj.current_rank_id,
                score_obj.version,
                ScoreAdjustment.objects.count(),
                RankChangeEvent.objects.count(),
                TeamRankAchievement.objects.count(),
                MessageDelivery.objects.count(),
            ),
            state_before,
        )


@override_settings(RATING_SECRET_ENCRYPTION_KEY='test-only-master')
class RatingDomainTests(TestCase):
    def setUp(self):
        self.city = city()
        self.actor = user(city_obj=self.city)
        self.team = team(
            self.actor,
            self.city,
            phone='+7 999 000-00-00',
            sms_allowed=True,
            consent_source='registration',
            consent_recorded_at='2026-09-17T12:00:00Z',
        )
        self.classic = score(self.team)

    def adjust(self, points, *, games=0, operation=None, expected=None,
               source=ScoreAdjustment.Source.GAME_RESULT, reason='Игра'):
        return apply_adjustment(
            actor=self.actor,
            team_score=self.classic,
            delta_points=points,
            delta_games=games,
            reason=reason,
            source=source,
            operation_id=operation or operation_id(),
            expected_version=expected,
        )

    def test_team_starts_with_three_isolated_zero_scores(self):
        self.assertEqual(RatingFormat.objects.count(), 3)
        self.assertEqual(
            list(RatingFormat.objects.order_by('order').values_list('code', flat=True)),
            ['classic', 'musicality', 'fans'],
        )
        self.assertEqual(Rank.objects.count(), 36)
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(self.team.scores.count(), 3)
        self.assertEqual(set(self.team.scores.values_list('points', flat=True)), {Decimal('0.0')})

    def test_database_constraints_reject_negative_score_totals(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TeamScore.objects.filter(pk=self.classic.pk).update(points=Decimal('-0.1'))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TeamScore.objects.filter(pk=self.classic.pk).update(games=-1)

    def test_decimal_tenths_are_exact_and_extra_precision_is_rejected(self):
        self.assertEqual(parse_points('87,5'), Decimal('87.5'))
        for invalid in ('87.49', '-0.01', 'NaN', 'Infinity'):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                parse_points(invalid)
        self.adjust('87,5')
        self.classic.refresh_from_db()
        self.assertEqual(self.classic.points, Decimal('87.5'))

    def test_rank_boundaries_are_inclusive_lower_bounds(self):
        ranks = list(self.classic.rating_format.ranks.order_by('min_points', 'level'))
        cases = (
            ('299', None), ('299.5', None), ('300', 1), ('699', 1),
            ('700', 2), ('1499', 2), ('1500', 3), ('9999', 11), ('10000', 12),
        )
        for points, level in cases:
            with self.subTest(points=points):
                found = rank_for_points(ranks, Decimal(points))
                self.assertEqual(found.level if found else None, level)
        for rank in ranks:
            with self.subTest(level=rank.level):
                self.assertEqual(
                    rank_for_points(ranks, Decimal(rank.min_points)).level, rank.level
                )

    def test_adjustment_preserves_other_format_and_rejects_negative_totals_atomically(self):
        musicality = score(self.team, 'musicality')
        self.adjust('300', games=1)
        musicality.refresh_from_db()
        self.assertEqual((musicality.points, musicality.games, musicality.current_rank_id), (0, 0, None))
        before = ScoreAdjustment.objects.count()
        with self.assertRaises(ValidationError):
            self.adjust('-301', games=-2, source=ScoreAdjustment.Source.CORRECTION)
        self.classic.refresh_from_db()
        self.assertEqual((self.classic.points, self.classic.games), (Decimal('300.0'), 1))
        self.assertEqual(ScoreAdjustment.objects.count(), before)

    def test_operation_id_is_idempotent_and_rejects_different_payload(self):
        op = operation_id()
        first, created = self.adjust('10', operation=op)
        repeated, repeated_created = self.adjust('10', operation=op)
        self.assertTrue(created)
        self.assertFalse(repeated_created)
        self.assertEqual(first.pk, repeated.pk)
        with self.assertRaises(IdempotencyConflict):
            self.adjust('11', operation=op)
        self.classic.refresh_from_db()
        self.assertEqual(self.classic.points, Decimal('10.0'))

    def test_expected_version_zero_is_enforced_after_first_write(self):
        self.adjust('10', expected=0)
        with self.assertRaises(ConcurrencyConflict):
            self.adjust('5', expected=0)
        self.classic.refresh_from_db()
        self.assertEqual((self.classic.points, self.classic.version), (Decimal('10.0'), 1))

    def test_multi_rank_crossing_creates_one_event_all_gifts_and_one_sms(self):
        adjustment, _ = self.adjust('2500', games=1)
        event = RankChangeEvent.objects.get(source_adjustment=adjustment)
        self.assertEqual((event.old_rank_level, event.new_rank_level), (None, 4))
        self.assertEqual(
            list(TeamRankAchievement.objects.filter(team_score=self.classic).values_list('rank__level', flat=True)),
            [1, 2, 3, 4],
        )
        self.assertEqual(MessageDelivery.objects.filter(event=event).count(), 1)
        self.assertEqual(
            TeamRankAchievement.objects.get(team_score=self.classic, rank__level=4).gift_status,
            TeamRankAchievement.GiftStatus.PENDING,
        )

    def test_reversal_is_append_only_and_repeat_rank_has_no_duplicate_gift_or_sms(self):
        original, _ = self.adjust('2500')
        reversal, created = reverse_adjustment(
            actor=self.actor, adjustment=original, operation_id=operation_id(), reason='Исправление'
        )
        self.assertTrue(created)
        self.assertEqual(reversal.reverses_id, original.pk)
        self.assertEqual(original.author_id, self.actor.pk)
        self.assertTrue(original.created_at)
        self.assertEqual(original.reason, 'Игра')
        with self.assertRaises(ProtectedError):
            original.delete()
        self.classic.refresh_from_db()
        self.assertEqual(self.classic.points, 0)
        self.adjust('2500')
        self.assertEqual(TeamRankAchievement.objects.filter(team_score=self.classic).count(), 4)
        self.assertEqual(MessageDelivery.objects.count(), 1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ScoreAdjustment.objects.create(
                    operation_id=uuid.uuid4(), payload_hash='x', team_score=self.classic,
                    delta_points=Decimal('0.0'), delta_games=0, reason='invalid',
                    source=ScoreAdjustment.Source.CORRECTION, author=self.actor,
                    points_before=0, points_after=0, games_before=0, games_after=0,
                )

    def test_no_rank_change_creates_neither_event_nor_sms(self):
        self.adjust('10')
        self.assertFalse(RankChangeEvent.objects.exists())
        self.assertFalse(MessageDelivery.objects.exists())

    def test_missing_phone_consent_and_template_are_visible_queue_states(self):
        cases = (
            ('missing_phone', '', True, 'registration', 'Команда {rating_url}'),
            ('consent_missing', '+79990000000', False, '', 'Команда {rating_url}'),
            ('template_missing', '+79990000000', True, 'registration', ''),
        )
        from rating.models import RatingPageSettings
        for index, (code, phone, allowed, consent, template) in enumerate(cases):
            with self.subTest(code=code):
                # Model legacy/imported rows which may predate current create-team validation.
                other = team(self.actor, self.city, name='Команда {}'.format(index))
                Team.objects.filter(pk=other.pk).update(
                    phone=phone,
                    sms_allowed=allowed,
                    consent_source=consent,
                    consent_recorded_at='2026-09-17T12:00:00Z' if allowed else None,
                )
                other.refresh_from_db()
                RatingPageSettings.objects.update_or_create(pk=1, defaults={'sms_template': template})
                apply_adjustment(
                    actor=self.actor, team_score=score(other), delta_points='300', delta_games=1,
                    reason='Игра', source=ScoreAdjustment.Source.GAME_RESULT,
                    operation_id=operation_id(), expected_version=0,
                )
                delivery = MessageDelivery.objects.filter(event__team_score__team=other).get()
                expected_status = MessageDelivery.Status.FAILED if code == 'template_missing' else MessageDelivery.Status.SKIPPED
                self.assertEqual((delivery.status, delivery.safe_error_code), (expected_status, code))

    def test_phone_change_requires_fresh_consent_and_disabling_sms_clears_consent(self):
        recorded_at = timezone.now()
        self.team.consent_recorded_at = recorded_at
        self.team.save(update_fields=('consent_recorded_at',))
        with self.assertRaises(ValidationError):
            update_team(
                actor=self.actor,
                team=self.team,
                phone='+79991112233',
                sms_allowed=True,
                consent_source=self.team.consent_source,
                consent_recorded_at=recorded_at,
            )
        self.team.refresh_from_db()
        self.assertEqual(self.team.phone, '+79990000000')

        fresh_consent_at = timezone.now()
        update_team(
            actor=self.actor,
            team=self.team,
            phone='+79991112233',
            sms_allowed=True,
            consent_source='phone-change-confirmation',
            consent_recorded_at=fresh_consent_at,
        )
        self.team.refresh_from_db()
        self.assertEqual(self.team.phone, '+79991112233')
        self.assertEqual(self.team.consent_source, 'phone-change-confirmation')

        update_team(
            actor=self.actor,
            team=self.team,
            phone='+79992223344',
            sms_allowed=False,
        )
        self.team.refresh_from_db()
        self.assertFalse(self.team.sms_allowed)
        self.assertEqual(self.team.consent_source, '')
        self.assertIsNone(self.team.consent_recorded_at)
        self.assertIsNone(self.team.consent_recorded_by_id)

    @override_settings(RATING_PUBLIC_URL_TEMPLATE='https://{missing}.example.test/rating/')
    def test_sms_render_configuration_failure_keeps_business_transaction_and_visible_outbox(self):
        settings = RatingPageSettings.get_solo()
        settings.sms_template = '{team} достигла {new_rank}: {rating_url}'
        settings.save(update_fields=('sms_template',))
        adjustment, created = self.adjust('300', games=1)
        self.assertTrue(created)
        self.classic.refresh_from_db()
        self.assertEqual((self.classic.points, self.classic.games), (Decimal('300.0'), 1))
        event = RankChangeEvent.objects.get(source_adjustment=adjustment)
        self.assertTrue(TeamRankAchievement.objects.filter(source_event=event).exists())
        delivery = MessageDelivery.objects.get(event=event)
        self.assertEqual(
            (delivery.status, delivery.safe_error_code, delivery.rendered_body),
            (MessageDelivery.Status.FAILED, 'template_render_error', ''),
        )

    def test_defensive_malformed_stored_sms_template_keeps_adjustment_and_audit(self):
        settings = RatingPageSettings.get_solo()
        settings.sms_template = '{team:bad} {rating_url}'
        settings.save(update_fields=('sms_template',))
        adjustment, created = self.adjust('300', games=1)
        self.assertTrue(created)
        self.classic.refresh_from_db()
        self.assertEqual(self.classic.points, Decimal('300.0'))
        event = RankChangeEvent.objects.get(source_adjustment=adjustment)
        self.assertEqual(MessageDelivery.objects.get(event=event).safe_error_code, 'template_render_error')
