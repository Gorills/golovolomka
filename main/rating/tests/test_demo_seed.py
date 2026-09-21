from collections import Counter
from io import StringIO
import os
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase

from rating.demo_seed import DEMO_MARKER, DemoSeedError, seed_demo
from rating.models import (
    GiftStatusChange,
    MessageDelivery,
    Rank,
    RatingFormat,
    ScoreAdjustment,
    SmsIntegrationSettings,
    Team,
    TeamRankAchievement,
    TeamScore,
)
from rating.services import normalize_team_name

from .factories import city, user


class DemoSeedTests(TestCase):
    def setUp(self):
        self.city = city('demo-city')
        self.actor = user('demo-root', superuser=True)
        self.unrelated = user('unrelated-user')

    def _catalog_snapshot(self):
        return list(
            Rank.objects.order_by('rating_format_id', 'level').values_list(
                'rating_format_id', 'level', 'min_points', 'name', 'description',
                'gift', 'logo', 'logo_alt', 'is_active'
            )
        )

    def test_seed_covers_rankings_history_gifts_and_safe_delivery_states(self):
        catalog_before = self._catalog_snapshot()
        format_before = list(
            RatingFormat.objects.order_by('id').values_list(
                'id', 'code', 'name', 'description', 'order', 'is_active', 'catalog_version'
            )
        )
        sms_before = list(SmsIntegrationSettings.objects.values())
        user_before = list(
            get_user_tuple
            for get_user_tuple in type(self.actor).objects.order_by('id').values_list(
                'id', 'username', 'is_active', 'is_staff', 'is_superuser'
            )
        )

        result = seed_demo(city=self.city, actor=self.actor)

        demo_teams = Team.objects.filter(city=self.city, private_note__startswith=DEMO_MARKER)
        scores = TeamScore.objects.filter(team__in=demo_teams).select_related('current_rank')
        self.assertEqual(result['demo_teams'], 30)
        self.assertEqual(result['demo_scores'], 90)
        self.assertEqual(demo_teams.count(), 30)
        self.assertEqual(scores.count(), 90)
        self.assertEqual(
            set(scores.values_list('rating_format__code', flat=True)),
            {'classic', 'musicality', 'fans'},
        )
        self.assertEqual(
            set(scores.exclude(current_rank=None).values_list('current_rank__level', flat=True)),
            set(range(1, 13)),
        )
        self.assertGreater(scores.filter(current_rank=None).count(), 0)
        self.assertTrue(all(score.points.as_tuple().exponent == -1 for score in scores))
        point_counts = Counter(scores.values_list('rating_format__code', 'points'))
        self.assertTrue(any(count > 1 for count in point_counts.values()))
        self.assertGreater(len(set(scores.values_list('games', flat=True))), 10)

        achievements = TeamRankAchievement.objects.filter(team_score__team__in=demo_teams)
        self.assertGreater(achievements.count(), 0)
        self.assertTrue(achievements.filter(gift_status='pending').exists())
        self.assertTrue(achievements.filter(gift_status='issued').exists())
        self.assertTrue(achievements.filter(gift_status='cancelled').exists())
        self.assertTrue(GiftStatusChange.objects.filter(achievement__in=achievements).exists())
        deliveries = MessageDelivery.objects.filter(event__team_score__team__in=demo_teams)
        self.assertTrue(deliveries.exists())
        self.assertEqual(
            deliveries.filter(status__in=('queued', 'processing', 'accepted')).count(), 0
        )
        self.assertFalse(demo_teams.exclude(phone='', sms_allowed=False).exists())

        self.assertEqual(self._catalog_snapshot(), catalog_before)
        self.assertEqual(
            list(
                RatingFormat.objects.order_by('id').values_list(
                    'id', 'code', 'name', 'description', 'order', 'is_active', 'catalog_version'
                )
            ),
            format_before,
        )
        self.assertEqual(list(SmsIntegrationSettings.objects.values()), sms_before)
        self.assertEqual(
            list(
                type(self.actor).objects.order_by('id').values_list(
                    'id', 'username', 'is_active', 'is_staff', 'is_superuser'
                )
            ),
            user_before,
        )

    def test_second_run_is_idempotent_and_does_not_overwrite(self):
        first = seed_demo(city=self.city, actor=self.actor)
        counts_before = (
            Team.objects.count(), TeamScore.objects.count(), ScoreAdjustment.objects.count(),
            TeamRankAchievement.objects.count(), GiftStatusChange.objects.count(),
            MessageDelivery.objects.count(),
        )
        team = Team.objects.get(private_note='{}:team:01'.format(DEMO_MARKER))
        team.captain_name = 'Ручная редакторская пометка'
        team.save(update_fields=('captain_name',))

        second = seed_demo(city=self.city, actor=self.actor)

        self.assertEqual(first['created_teams'], 30)
        self.assertEqual(second['created_teams'], 0)
        self.assertEqual(second['created_adjustments'], 0)
        self.assertEqual(second['reused_adjustments'], 90)
        self.assertEqual(
            (
                Team.objects.count(), TeamScore.objects.count(), ScoreAdjustment.objects.count(),
                TeamRankAchievement.objects.count(), GiftStatusChange.objects.count(),
                MessageDelivery.objects.count(),
            ),
            counts_before,
        )
        team.refresh_from_db()
        self.assertEqual(team.captain_name, 'Ручная редакторская пометка')

    def test_dry_run_rolls_back_every_change(self):
        output = StringIO()
        call_command(
            'rating_demo_seed',
            city=self.city.slug,
            actor_id=self.actor.pk,
            dry_run=True,
            stdout=output,
        )
        self.assertIn('DRY RUN', output.getvalue())
        self.assertFalse(Team.objects.filter(private_note__startswith=DEMO_MARKER).exists())
        self.assertFalse(
            ScoreAdjustment.objects.filter(reason__contains=DEMO_MARKER).exists()
        )
        self.assertEqual(MessageDelivery.objects.count(), 0)

    def test_name_collision_fails_atomically(self):
        Team.objects.create(
            city=self.city,
            name='ДЕМО · Команда 09',
            normalized_name=normalize_team_name('ДЕМО · Команда 09'),
            private_note='user-owned',
        )
        with self.assertRaises(DemoSeedError):
            seed_demo(city=self.city, actor=self.actor)
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(TeamScore.objects.count(), 0)
        self.assertEqual(ScoreAdjustment.objects.count(), 0)

    def test_seed_owned_team_with_contact_data_fails_without_overwrite(self):
        seed_demo(city=self.city, actor=self.actor)
        team = Team.objects.get(private_note='{}:team:01'.format(DEMO_MARKER))
        team.phone = '+79991234567'
        team.sms_allowed = True
        team.consent_source = 'manually edited'
        team.save(update_fields=('phone', 'sms_allowed', 'consent_source'))
        counts_before = (
            Team.objects.count(), ScoreAdjustment.objects.count(), MessageDelivery.objects.count()
        )
        with self.assertRaises(DemoSeedError):
            seed_demo(city=self.city, actor=self.actor)
        team.refresh_from_db()
        self.assertEqual(team.phone, '+79991234567')
        self.assertEqual(
            (Team.objects.count(), ScoreAdjustment.objects.count(), MessageDelivery.objects.count()),
            counts_before,
        )

    def test_command_refuses_unsafe_sms_configuration(self):
        sms = SmsIntegrationSettings.get_solo()
        sms.sending_enabled = True
        sms.save(update_fields=('sending_enabled',))
        with self.assertRaisesMessage(CommandError, 'SMS settings are not safe'):
            call_command(
                'rating_demo_seed',
                city=self.city.slug,
                actor_id=self.actor.pk,
                dry_run=True,
            )
        self.assertFalse(Team.objects.filter(private_note__startswith=DEMO_MARKER).exists())

    def test_command_refuses_unexpected_persistent_sqlite_path(self):
        with mock.patch.dict(os.environ, {'DJANGO_SETTINGS_MODULE': 'main.settings'}):
            with mock.patch.dict(
                connection.settings_dict,
                {'NAME': '/tmp/not-the-active-rating-database.sqlite3'},
            ):
                with self.assertRaisesMessage(
                    CommandError, 'SQLite path is not the expected local database'
                ):
                    call_command(
                        'rating_demo_seed',
                        city=self.city.slug,
                        actor_id=self.actor.pk,
                        dry_run=True,
                    )
        self.assertFalse(Team.objects.filter(private_note__startswith=DEMO_MARKER).exists())
