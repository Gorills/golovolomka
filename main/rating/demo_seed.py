import uuid
from decimal import Decimal

from django.db import transaction

from .models import (
    MessageDelivery,
    Rank,
    RatingFormat,
    ScoreAdjustment,
    Team,
    TeamRankAchievement,
    TeamScore,
)
from .services import (
    IdempotencyConflict,
    apply_adjustment,
    create_team,
    normalize_team_name,
    update_gift_status,
)


DEMO_MARKER = 'rating-demo:v1'
DEMO_NAMESPACE = uuid.UUID('d4e3e1e4-46a1-5fcc-b10b-7f67b2f35e42')
DEMO_TEAM_COUNT = 30
EXPECTED_FORMAT_CODES = ('classic', 'musicality', 'fans')
TARGET_LEVELS = (
    None, 1, 2, 3, 4, 5, 6, 7, 8, 9,
    10, 11, 12, 12, 6, 6, None, 3, 4, 5,
    7, 8, 9, 10, 11, 12, 1, 2, 4, 5,
)


class DemoSeedError(Exception):
    pass


def _operation_id(*parts):
    return uuid.uuid5(DEMO_NAMESPACE, ':'.join(str(part) for part in parts))


def _team_name(number):
    return 'ДЕМО · Команда {:02d}'.format(number)


def _team_marker(number):
    return '{}:team:{:02d}'.format(DEMO_MARKER, number)


def _catalog():
    formats = list(RatingFormat.objects.all().order_by('order', 'id'))
    codes = tuple(item.code for item in formats)
    if len(formats) != 3 or set(codes) != set(EXPECTED_FORMAT_CODES):
        raise DemoSeedError(
            'Demo seed requires exactly the classic, musicality and fans formats'
        )
    ranks_by_format = {}
    for rating_format in formats:
        ranks = list(
            Rank.objects.filter(rating_format=rating_format, is_active=True).order_by('level')
        )
        if [rank.level for rank in ranks] != list(range(1, 13)):
            raise DemoSeedError(
                'Demo seed requires 12 active rank levels for {}'.format(rating_format.code)
            )
        thresholds = [rank.min_points for rank in ranks]
        if thresholds != sorted(thresholds) or len(set(thresholds)) != 12 or thresholds[0] <= 0:
            raise DemoSeedError(
                'Demo seed requires strictly increasing positive thresholds for {}'.format(
                    rating_format.code
                )
            )
        ranks_by_format[rating_format.code] = ranks
    return formats, ranks_by_format


def _points_for_level(ranks, level):
    if level is None:
        return Decimal(ranks[0].min_points) - Decimal('0.5')
    return Decimal(ranks[level - 1].min_points) + Decimal('0.5')


def _preflight_teams(city):
    existing = {}
    for number in range(1, DEMO_TEAM_COUNT + 1):
        name = _team_name(number)
        marker = _team_marker(number)
        marked = list(Team.objects.filter(city=city, private_note=marker).order_by('id'))
        matches = list(
            Team.objects.filter(city=city, normalized_name=normalize_team_name(name)).order_by('id')
        )
        if marked:
            if len(marked) != 1 or len(matches) != 1 or marked[0].pk != matches[0].pk:
                raise DemoSeedError('Demo marker collision: {}'.format(marker))
            if (
                marked[0].phone
                or marked[0].sms_allowed
                or marked[0].consent_source
                or marked[0].consent_recorded_at is not None
            ):
                raise DemoSeedError('Demo team contains contact or consent data: {}'.format(name))
            existing[number] = marked[0]
            continue
        if not matches:
            continue
        if len(matches) != 1 or matches[0].private_note != marker:
            raise DemoSeedError('Team name collision: {}'.format(name))
        existing[number] = matches[0]
    return existing


def _ensure_clean_score(score, operation_id):
    if ScoreAdjustment.objects.filter(operation_id=operation_id).exists():
        return
    if (
        score.points != 0
        or score.games != 0
        or score.version != 0
        or score.current_rank_id is not None
        or score.adjustments.exists()
    ):
        raise DemoSeedError(
            'Demo score has data without its deterministic operation: {}'.format(score.pk)
        )


@transaction.atomic
def seed_demo(*, city, actor):
    if not actor.is_active or not actor.is_superuser:
        raise DemoSeedError('Actor must be an active superuser')
    formats, ranks_by_format = _catalog()
    existing = _preflight_teams(city)
    teams = []
    created_teams = 0
    created_adjustments = 0
    reused_adjustments = 0
    for number in range(1, DEMO_TEAM_COUNT + 1):
        team = existing.get(number)
        if team is None:
            team = create_team(
                actor=actor,
                city=city,
                name=_team_name(number),
                phone='',
                sms_allowed=False,
                private_note=_team_marker(number),
            )
            created_teams += 1
        teams.append(team)
        scores = {
            score.rating_format.code: score
            for score in TeamScore.objects.select_related(
                'team__city', 'rating_format', 'current_rank'
            ).filter(team=team)
        }
        if set(scores) != set(EXPECTED_FORMAT_CODES):
            raise DemoSeedError('Demo team has an unexpected score set: {}'.format(team.pk))
        for format_offset, rating_format in enumerate(formats):
            score = scores[rating_format.code]
            level = TARGET_LEVELS[(number - 1 + format_offset * 7) % len(TARGET_LEVELS)]
            points = _points_for_level(ranks_by_format[rating_format.code], level)
            games = 1 + ((number * 3 + format_offset * 5) % 17)
            operation_id = _operation_id(city.slug, number, rating_format.code, 'score')
            _ensure_clean_score(score, operation_id)
            try:
                adjustment, created = apply_adjustment(
                    actor=actor,
                    team_score=score,
                    delta_points=points,
                    delta_games=games,
                    reason='ДЕМО: исходное наполнение рейтинга ({})'.format(DEMO_MARKER),
                    source=ScoreAdjustment.Source.GAME_RESULT,
                    operation_id=operation_id,
                )
            except IdempotencyConflict as exc:
                raise DemoSeedError(str(exc))
            if created:
                created_adjustments += 1
            else:
                reused_adjustments += 1
            achievement = TeamRankAchievement.objects.filter(
                team_score=score,
                rank__level=level,
            ).first() if level is not None else None
            if achievement and achievement.gift_snapshot:
                status = None
                if (number + format_offset) % 3 == 1:
                    status = TeamRankAchievement.GiftStatus.ISSUED
                elif (number + format_offset) % 3 == 2:
                    status = TeamRankAchievement.GiftStatus.CANCELLED
                if status:
                    update_gift_status(
                        actor=actor,
                        achievement=achievement,
                        status=status,
                        comment='ДЕМО: пример статуса подарка',
                        operation_id=_operation_id(
                            city.slug, number, rating_format.code, 'gift', status
                        ),
                    )
    team_ids = [team.pk for team in teams]
    score_rows = TeamScore.objects.filter(team_id__in=team_ids)
    achievement_rows = TeamRankAchievement.objects.filter(team_score__team_id__in=team_ids)
    delivery_rows = MessageDelivery.objects.filter(event__team_score__team_id__in=team_ids)
    result = {
        'created_teams': created_teams,
        'reused_teams': DEMO_TEAM_COUNT - created_teams,
        'demo_teams': len(team_ids),
        'demo_scores': score_rows.count(),
        'created_adjustments': created_adjustments,
        'reused_adjustments': reused_adjustments,
        'no_rank_scores': score_rows.filter(current_rank__isnull=True).count(),
        'achievements': achievement_rows.count(),
        'gift_pending': achievement_rows.filter(
            gift_status=TeamRankAchievement.GiftStatus.PENDING
        ).count(),
        'gift_issued': achievement_rows.filter(
            gift_status=TeamRankAchievement.GiftStatus.ISSUED
        ).count(),
        'gift_cancelled': achievement_rows.filter(
            gift_status=TeamRankAchievement.GiftStatus.CANCELLED
        ).count(),
        'deliveries': delivery_rows.count(),
        'sending_eligible_deliveries': delivery_rows.filter(
            status__in=(
                MessageDelivery.Status.QUEUED,
                MessageDelivery.Status.PROCESSING,
                MessageDelivery.Status.ACCEPTED,
            )
        ).count(),
    }
    if result['sending_eligible_deliveries']:
        raise DemoSeedError('Demo seed created a sending-eligible message delivery')
    return result
