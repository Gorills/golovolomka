from django.core.management.base import BaseCommand, CommandError

from rating.queue import poll_batch


class Command(BaseCommand):
    help = 'Poll delivery statuses for accepted rating SMS messages.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        if options['limit'] < 1 or options['limit'] > 500:
            raise CommandError('limit must be between 1 and 500')
        result = poll_batch(limit=options['limit'])
        self.stdout.write('processed={} paused={}'.format(result['processed'], result['paused']))
