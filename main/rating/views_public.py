from types import SimpleNamespace

from django.core.paginator import Paginator
from django.db.models import F, IntegerField, Value
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import render

from home.city import get_subdomain

from .models import Rank, RatingFormat, RatingPageSettings, TeamScore
from .services import gifts_for_ranks, normalize_team_name


SORTS = {
    'points': 'points',
    'rank': 'rank_level',
    'name': 'team__normalized_name',
    'games': 'games',
}


def _format_dto(item):
    return SimpleNamespace(code=item.code, name=item.name, description=item.description)


def _rank_dto(item, gift=None):
    logo_url = item.logo.url if item.logo else ''
    return SimpleNamespace(
        level=item.level,
        name=item.name,
        min_points=item.min_points,
        logo_url=logo_url,
        logo_alt=item.logo_alt,
        description=item.description,
        gift=item.gift if gift is None else gift,
    )


def rating_public(request):
    city = get_subdomain(request)
    if city is None:
        raise Http404('Город не определён')
    formats = list(RatingFormat.objects.filter(is_active=True).order_by('order', 'id'))
    if not formats:
        raise Http404('Форматы рейтинга не настроены')
    code = request.GET.get('format', '')
    current = next((item for item in formats if item.code == code), formats[0])
    search = (request.GET.get('q') or '').strip()[:100]
    sort = request.GET.get('sort', 'points')
    if sort not in SORTS:
        sort = 'points'
    direction = request.GET.get('direction', 'desc' if sort == 'points' else 'asc')
    if direction not in ('asc', 'desc'):
        direction = 'desc' if sort == 'points' else 'asc'
    scores = (
        TeamScore.objects.filter(
            team__city=city, team__is_active=True, rating_format=current
        )
        .select_related('team', 'current_rank')
        .annotate(
            rank_level=Coalesce('current_rank__level', Value(0), output_field=IntegerField())
        )
    )
    if search:
        scores = scores.filter(team__normalized_name__icontains=normalize_team_name(search))
    primary = SORTS[sort]
    ordering = ('-' + primary) if direction == 'desc' else primary
    scores = scores.order_by(ordering, 'team__normalized_name', 'team_id')
    paginator = Paginator(scores, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    all_ranks = list(
        Rank.objects.filter(rating_format__in=formats, is_active=True)
        .select_related('rating_format')
        .order_by('rating_format__order', 'min_points', 'level')
    )
    ranks = [rank for rank in all_ranks if rank.rating_format_id == current.pk]
    effective_gifts = gifts_for_ranks(city_id=city.pk, ranks=all_ranks)
    gifts_by_format = {item.pk: [] for item in formats}
    for rank in all_ranks:
        gift = effective_gifts[rank.pk]
        if gift:
            gifts_by_format[rank.rating_format_id].append(_rank_dto(rank, gift))
    start = (page_obj.number - 1) * paginator.per_page
    rows = []
    for offset, score in enumerate(page_obj.object_list, start=1):
        next_rank = next((rank for rank in ranks if rank.min_points > score.points), None)
        rows.append(
            SimpleNamespace(
                number=start + offset,
                team_name=score.team.name,
                games=score.games,
                points=score.points,
                current_rank=_rank_dto(score.current_rank) if score.current_rank else None,
                points_to_next=(next_rank.min_points - score.points) if next_rank else None,
            )
        )
    page_obj.object_list = rows
    page_settings = RatingPageSettings.get_solo()
    city_suffix = ' — {}'.format(city.name)
    safe_settings = SimpleNamespace(
        intro_title=(page_settings.intro_title or 'Рейтинг команд') + city_suffix,
        intro_text=page_settings.intro_text,
        gifts_title=page_settings.gifts_title,
        gifts_text=page_settings.gifts_text,
        seo_title=(page_settings.seo_title or 'Рейтинг команд'),
        seo_description=(page_settings.seo_description or 'Рейтинг команд') + city_suffix,
    )
    return render(
        request,
        'rating/public/rating.html',
        {
            'formats': [_format_dto(item) for item in formats],
            'current_format': _format_dto(current),
            'page_obj': page_obj,
            'search': search,
            'sort': sort,
            'direction': direction,
            'ranks': [_rank_dto(item, effective_gifts[item.pk]) for item in ranks],
            'gift_groups': [
                SimpleNamespace(
                    format=_format_dto(item),
                    gifts=gifts_by_format[item.pk],
                )
                for item in formats
            ],
            'current_city': SimpleNamespace(name=city.name, slug=city.slug),
            'settings': safe_settings,
            'canonical_url': request.build_absolute_uri(request.path),
        },
    )
