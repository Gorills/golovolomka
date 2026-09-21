from django.core.management.base import BaseCommand

from rating.models import Rank, RatingFormat, RatingPageSettings, SmsIntegrationSettings
from rating.seed import seed_catalog


class Command(BaseCommand):
    help = 'Idempotently seed the rating formats, ranks and singleton settings.'

    def handle(self, *args, **options):
        result = seed_catalog(RatingFormat, Rank, RatingPageSettings, SmsIntegrationSettings)
        self.stdout.write(
            self.style.SUCCESS(
                'Rating catalog ready: {} formats, {} ranks; created {} formats, {} ranks'.format(
                    RatingFormat.objects.count(), Rank.objects.count(),
                    result['created_formats'], result['created_ranks'],
                )
            )
        )
        for conflict in result['skipped_rank_conflicts']:
            self.stdout.write(
                self.style.WARNING(
                    'Skipped missing seed rank {format_code}/level {level}: '
                    'threshold {min_points} is already used'.format(**conflict)
                )
            )
