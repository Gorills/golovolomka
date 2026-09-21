import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from home.models import City
from rating.demo_seed import DemoSeedError, seed_demo
from rating.models import MessageDelivery, SmsIntegrationSettings


class Command(BaseCommand):
    help = 'Safely create deterministic local demo rating data for one existing city.'

    def add_arguments(self, parser):
        parser.add_argument('--city', required=True, help='Existing city slug')
        parser.add_argument('--actor-id', required=True, type=int, help='Active superuser ID')
        parser.add_argument('--dry-run', action='store_true', help='Validate and roll back all writes')

    def _assert_safe_environment(self):
        if connection.vendor != 'sqlite':
            raise CommandError('rating_demo_seed is restricted to local SQLite')
        database_name = str(connection.settings_dict.get('NAME') or '')
        settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '')
        is_django_test_memory = (
            database_name.startswith('file:memorydb_')
            and database_name.endswith('?mode=memory&cache=shared')
        )
        if is_django_test_memory:
            pass
        elif settings_module == 'main.settings_rating_test':
            expected = os.environ.get('RATING_TEST_DB', '')
            if not expected or Path(database_name).resolve() != Path(expected).resolve():
                raise CommandError('SQLite path does not match RATING_TEST_DB')
        else:
            expected = Path(settings.BASE_DIR) / 'db.sqlite3'
            if not database_name or Path(database_name).resolve() != expected.resolve():
                raise CommandError('SQLite path is not the expected local database')
        sms = SmsIntegrationSettings.objects.filter(pk=1).first()
        if (
            sms is None
            or sms.sending_enabled
            or not sms.emergency_stop
            or not sms.test_mode
            or bool(sms.api_key_ciphertext)
            or bool(os.environ.get('SMSPILOT_API_KEY'))
        ):
            raise CommandError('SMS settings are not safe for demo seeding')
        if MessageDelivery.objects.filter(
            status__in=(
                MessageDelivery.Status.QUEUED,
                MessageDelivery.Status.PROCESSING,
                MessageDelivery.Status.ACCEPTED,
            )
        ).exists():
            raise CommandError('Sending-eligible message deliveries already exist')

    def handle(self, *args, **options):
        self._assert_safe_environment()
        city = City.objects.filter(slug=options['city']).first()
        if city is None:
            raise CommandError('Unknown city slug')
        actor = get_user_model().objects.filter(pk=options['actor_id']).first()
        if actor is None or not actor.is_active or not actor.is_superuser:
            raise CommandError('Actor must be an active superuser')
        try:
            with transaction.atomic():
                result = seed_demo(city=city, actor=actor)
                if options['dry_run']:
                    transaction.set_rollback(True)
        except DemoSeedError as exc:
            raise CommandError(str(exc))
        mode = 'DRY RUN' if options['dry_run'] else 'APPLIED'
        self.stdout.write(
            self.style.SUCCESS(
                '{}: city={} teams={} scores={} created_teams={} '
                'created_adjustments={} achievements={} gifts={}/{}/{} '
                'deliveries={} sending_eligible={}'.format(
                    mode,
                    city.slug,
                    result['demo_teams'],
                    result['demo_scores'],
                    result['created_teams'],
                    result['created_adjustments'],
                    result['achievements'],
                    result['gift_pending'],
                    result['gift_issued'],
                    result['gift_cancelled'],
                    result['deliveries'],
                    result['sending_eligible_deliveries'],
                )
            )
        )
