import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from home.models import City
from rating.models import (
    CityRatingAccess,
    MessageDelivery,
    RankChangeEvent,
    RatingFormat,
    Team,
    TeamScore,
)
from rating.services import create_team


def city(slug='nsk'):
    return City.objects.create(
        name=slug.upper(),
        slug=slug,
        phone='+70000000000',
        address='Тестовый адрес',
        email='test@example.com',
        vk='',
        instagram='',
        telegram='',
        whatsapp='',
    )


def user(username='operator', *, city_obj=None, superuser=False, active=True):
    account = get_user_model().objects.create_user(
        username=username,
        email='{}@example.com'.format(username),
        password='test-password',
        is_active=active,
        is_staff=superuser,
        is_superuser=superuser,
    )
    if city_obj is not None and not superuser:
        CityRatingAccess.objects.create(user=account, city=city_obj)
    return account


def team(actor, city_obj, name='Команда', **kwargs):
    return create_team(actor=actor, city=city_obj, name=name, **kwargs)


def score(team_obj, code='classic'):
    return TeamScore.objects.select_related('team__city', 'rating_format', 'current_rank').get(
        team=team_obj, rating_format__code=code
    )


def bare_team(city_obj, name='Команда'):
    item = Team.objects.create(city=city_obj, name=name, normalized_name=name.casefold())
    rating_format = RatingFormat.objects.get(code='classic')
    return item, TeamScore.objects.create(team=item, rating_format=rating_format)


def delivery_for(score_obj, *, status=MessageDelivery.Status.QUEUED, body='Тест'):
    event = RankChangeEvent.objects.create(
        team_score=score_obj,
        source=RankChangeEvent.Source.MAINTENANCE,
        direction=RankChangeEvent.Direction.INCREASE,
        new_rank=score_obj.rating_format.ranks.order_by('level').first(),
        new_rank_level=1,
        new_rank_name='Ранг 1',
    )
    return MessageDelivery.objects.create(
        event=event,
        recipient='+79990000000',
        rendered_body=body,
        status=status,
        expires_at=timezone.now() + timedelta(days=3),
        next_attempt_at=timezone.now(),
    )


def operation_id():
    return uuid.uuid4()
