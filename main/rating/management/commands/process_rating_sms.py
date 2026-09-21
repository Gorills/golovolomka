from django.core.management.base import BaseCommand, CommandError

from rating.queue import process_batch


class Command(BaseCommand):
    help = 'Process a bounded batch of durable rating SMS deliveries.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50)

    def handle(self, *args, **options):
        if options['limit'] < 1 or options['limit'] > 500:
            raise CommandError('limit must be between 1 and 500')
        result = process_batch(limit=options['limit'])
        self.stdout.write('processed={} paused={}'.format(result['processed'], result['paused']))
