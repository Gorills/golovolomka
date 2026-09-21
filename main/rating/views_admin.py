import hashlib
import json
import os
import uuid
from decimal import Decimal
from types import SimpleNamespace

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import CharField, DecimalField, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from home.city import is_local_city_dev
from home.models import City

from .forms import (
    AcknowledgeEventForm,
    AdjustmentCommitForm,
    BulkCommitForm,
    BulkMessageForm,
    CitySelectForm,
    CityRankGiftForm,
    GamesAdjustmentForm,
    GiftStatusForm,
    MessageRetryForm,
    ReversalForm,
    RankForm,
    RatingFormatForm,
    RatingPageSettingsForm,
    ScoreAdjustmentForm,
    SmsIntegrationSettingsForm,
    TeamForm,
)
from .models import (
    CityRatingAccess,
    CityRankGift,
    MessageDelivery,
    MessageAttempt,
    Rank,
    RankChangeEvent,
    RatingFormat,
    RatingPageSettings,
    ScoreAdjustment,
    SmsIntegrationSettings,
    Team,
    TeamRankAchievement,
    TeamScore,
)
from .secrets import encrypt_secret
from .provider import SmsPilotClient
from .services import (
    ConcurrencyConflict,
    IdempotencyConflict,
    PermissionDenied,
    RatingError,
    StalePreview,
    ValidationError,
    acknowledge_event,
    apply_adjustment,
    build_rank_preview,
    commit_rank_preview,
    create_team,
    clear_city_rank_gift,
    gifts_for_ranks,
    mask_phone,
    normalize_team_name,
    rank_for_points,
    request_manual_retry,
    reverse_adjustment,
    recalculate_format_scores,
    set_city_rank_gift,
    update_gift_status,
    update_team,
)


CITY_SESSION_KEY = 'rating_admin_city_id'


def _visible_cities(user):
    if user.is_superuser:
        return City.objects.all().order_by('name', 'id')
    return City.objects.filter(
        rating_accesses__user=user, rating_accesses__is_active=True
    ).distinct().order_by('name', 'id')


def _current_city(request, required=True):
    if not request.user.is_authenticated or not request.user.is_active:
        raise DjangoPermissionDenied
    cities = _visible_cities(request.user)
    count = cities.count()
    if count == 0:
        raise DjangoPermissionDenied
    if count == 1:
        city = cities.first()
        request.session[CITY_SESSION_KEY] = city.pk
        return city
    city_id = request.session.get(CITY_SESSION_KEY)
    city = cities.filter(pk=city_id).first() if city_id else None
    if city is None and required:
        raise DjangoPermissionDenied('Сначала выберите город')
    return city


def _capabilities(user):
    city_ops = bool(user.is_authenticated and user.is_active)
    return {
        'manage_teams': city_ops,
        'adjust_scores': city_ops,
        'view_contacts': city_ops,
        'ack_events': city_ops,
        'manage_gifts': city_ops,
        'manage_city_gifts': city_ops,
        'retry_sms': city_ops,
        'manage_catalog': bool(user.is_superuser),
        'manage_integration': bool(user.is_superuser),
    }


def _format_dto(item):
    return SimpleNamespace(code=item.code, name=item.name)


def _score_dto(score):
    return SimpleNamespace(
        id=score.pk,
        format_code=score.rating_format.code,
        format_name=score.rating_format.name,
        points=score.points,
        games=score.games,
        rank_name=score.current_rank.name if score.current_rank else '',
        version=score.version,
        adjust_url=reverse(
            'rating_admin:score_adjust',
            args=(score.team_id, score.rating_format.code),
        ),
    )


def _common(request, city=None):
    cities = list(_visible_cities(request.user))
    formats = list(RatingFormat.objects.filter(is_active=True).order_by('order', 'id'))
    counts = {'unacknowledged_count': 0, 'message_incident_count': 0}
    if city:
        counts['unacknowledged_count'] = RankChangeEvent.objects.filter(
            team_score__team__city=city,
            direction=RankChangeEvent.Direction.INCREASE,
            acknowledged_at__isnull=True,
        ).count()
        counts['message_incident_count'] = MessageDelivery.objects.filter(
            event__team_score__team__city=city,
            status__in=(MessageDelivery.Status.FAILED, MessageDelivery.Status.UNKNOWN),
        ).count()
    public_rating_url = ''
    if city:
        if is_local_city_dev(request):
            public_rating_url = '{}?city={}'.format(reverse('rating:public'), city.slug)
        else:
            public_rating_url = settings.RATING_PUBLIC_URL_TEMPLATE.format(city=city.slug)
    return {
        'current_city': city,
        'available_cities': cities,
        'city_select_form': CitySelectForm(cities=cities) if len(cities) > 1 else None,
        'capabilities': _capabilities(request.user),
        'formats': [_format_dto(item) for item in formats],
        'public_rating_url': public_rating_url,
        **counts,
    }


def _scoped_team(request, team_id):
    city = _current_city(request)
    return get_object_or_404(Team, pk=team_id, city=city), city


def _scoped_score(request, team_id, format_code):
    team, city = _scoped_team(request, team_id)
    score = get_object_or_404(
        TeamScore.objects.select_related('team__city', 'rating_format', 'current_rank'),
        team=team,
        rating_format__code=format_code,
    )
    return score, city


def _domain_error_response(request, exc, template=None, context=None):
    status = 409 if isinstance(exc, (IdempotencyConflict, ConcurrencyConflict, StalePreview)) else 400
    if template:
        context = dict(context or {})
        context['domain_error'] = str(exc) or exc.code
        return render(request, template, context, status=status)
    return HttpResponse(str(exc) or exc.code, status=status)


@login_required
@require_POST
def city_select(request):
    form = CitySelectForm(request.POST, cities=_visible_cities(request.user))
    if not form.is_valid():
        return HttpResponseBadRequest('Некорректный город')
    city = get_object_or_404(_visible_cities(request.user), slug=form.cleaned_data['city'])
    request.session[CITY_SESSION_KEY] = city.pk
    target = form.cleaned_data.get('next') or reverse('rating_admin:team_list')
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = reverse('rating_admin:team_list')
    return redirect(target)


@login_required
def team_list(request):
    city = _current_city(request, required=False)
    context = _common(request, city)
    if city is None:
        context['page_obj'] = Paginator(Team.objects.none(), 25).get_page(1)
        return render(request, 'rating/admin/team_list.html', context)
    search = (request.GET.get('q') or '').strip()[:100]
    status_filter = request.GET.get('status', 'active')
    current_code = request.GET.get('format', '')
    formats = list(RatingFormat.objects.filter(is_active=True).order_by('order', 'id'))
    current = next((item for item in formats if item.code == current_code), formats[0] if formats else None)
    teams = Team.objects.filter(city=city)
    if status_filter == 'archived':
        teams = teams.filter(is_active=False)
    elif status_filter != 'all':
        status_filter = 'active'
        teams = teams.filter(is_active=True)
    if search:
        teams = teams.filter(
            Q(normalized_name__icontains=normalize_team_name(search))
            | Q(captain_name__icontains=search)
            | Q(phone__icontains=search)
        )
    points_field = DecimalField(max_digits=18, decimal_places=1)
    if current:
        selected_score = TeamScore.objects.filter(
            team_id=OuterRef('pk'), rating_format=current
        )
        teams = teams.annotate(
            selected_points=Coalesce(
                Subquery(selected_score.values('points')[:1], output_field=points_field),
                Value(Decimal('0.0'), output_field=points_field),
            ),
            selected_games=Coalesce(
                Subquery(selected_score.values('games')[:1], output_field=IntegerField()),
                Value(0),
            ),
            selected_rank_level=Coalesce(
                Subquery(
                    selected_score.values('current_rank__level')[:1],
                    output_field=IntegerField(),
                ),
                Value(0),
            ),
            selected_rank_name=Coalesce(
                Subquery(
                    selected_score.values('current_rank__name')[:1],
                    output_field=CharField(),
                ),
                Value(''),
            ),
        )
    else:
        teams = teams.annotate(
            selected_points=Value(Decimal('0.0'), output_field=points_field),
            selected_games=Value(0, output_field=IntegerField()),
            selected_rank_level=Value(0, output_field=IntegerField()),
            selected_rank_name=Value('', output_field=CharField()),
        )
    sort = request.GET.get('sort', 'name')
    if sort not in ('points', 'rank', 'name', 'games'):
        sort = 'name'
    direction = request.GET.get(
        'direction', 'desc' if sort in ('points', 'rank', 'games') else 'asc'
    )
    if direction not in ('asc', 'desc'):
        direction = 'asc'
    primary = {
        'points': 'selected_points',
        'rank': 'selected_rank_level',
        'games': 'selected_games',
        'name': 'normalized_name',
    }[sort]
    teams = teams.order_by(
        ('-' if direction == 'desc' else '') + primary,
        'normalized_name',
        'id',
    )
    page_obj = Paginator(teams, 25).get_page(request.GET.get('page'))
    page_obj.object_list = [
        SimpleNamespace(
            id=team.pk,
            name=team.name,
            captain_name=team.captain_name,
            captain=team.captain_name,
            masked_phone=mask_phone(team.phone),
            is_active=team.is_active,
            points=team.selected_points,
            games=team.selected_games,
            current_rank=(
                SimpleNamespace(name=team.selected_rank_name, level=team.selected_rank_level)
                if team.selected_rank_name else None
            ),
            rank_name=team.selected_rank_name,
        )
        for team in page_obj.object_list
    ]
    context.update(
        {
            'page_obj': page_obj,
            'search': search,
            'status_filter': status_filter,
            'current_format': _format_dto(current) if current else None,
            'sort': sort,
            'direction': direction,
        }
    )
    return render(request, 'rating/admin/team_list.html', context)


@login_required
def team_create(request):
    city = _current_city(request)
    form = TeamForm(request.POST or None, city=city)
    if request.method == 'POST' and form.is_valid():
        try:
            values = dict(form.cleaned_data)
            values.pop('confirm_duplicate', None)
            team = create_team(actor=request.user, city=city, **values)
        except RatingError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, 'Команда создана')
            return redirect('rating_admin:team_detail', team_id=team.pk)
    context = _common(request, city)
    context.update({'form': form, 'team': None, 'is_create': True})
    return render(request, 'rating/admin/team_form.html', context)


@login_required
def team_edit(request, team_id):
    team, city = _scoped_team(request, team_id)
    initial = {
        'name': team.name,
        'captain_name': team.captain_name,
        'phone': team.phone,
        'sms_allowed': team.sms_allowed,
        'consent_source': team.consent_source,
        'consent_recorded_at': team.consent_recorded_at,
        'private_note': team.private_note,
    }
    form = TeamForm(request.POST or None, initial=initial, city=city, team=team)
    if request.method == 'POST' and form.is_valid():
        try:
            values = dict(form.cleaned_data)
            values.pop('confirm_duplicate', None)
            update_team(actor=request.user, team=team, **values)
        except RatingError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, 'Команда обновлена')
            return redirect('rating_admin:team_detail', team_id=team.pk)
    context = _common(request, city)
    context.update({'form': form, 'team': team, 'is_create': False})
    return render(request, 'rating/admin/team_form.html', context)


@login_required
def team_detail(request, team_id):
    team, city = _scoped_team(request, team_id)
    raw_scores = list(team.scores.select_related('rating_format', 'current_rank').order_by('rating_format__order'))
    scores = [_score_dto(score) for score in raw_scores]
    raw_achievements = list(
        TeamRankAchievement.objects.filter(team_score__team=team)
        .select_related('rank', 'team_score__rating_format')
        .order_by('team_score__rating_format__order', 'rank__level')
    )
    achievements = []
    for item in raw_achievements:
        gift_form = (
            GiftStatusForm(initial={'status': item.gift_status, 'operation_id': uuid.uuid4()})
            if item.gift_snapshot else None
        )
        achievements.append(
            SimpleNamespace(
                id=item.pk,
                format_name=item.team_score.rating_format.name,
                rank_name=item.rank_name_snapshot,
                achieved_at=item.first_achieved_at,
                gift_text=item.gift_snapshot,
                gift_status=item.gift_status or 'none',
                gift_status_label=(item.get_gift_status_display() if item.gift_status else 'Без подарка'),
                gift_form=gift_form,
            )
        )
    adjustments = [
        SimpleNamespace(
            created_at=item.created_at,
            format_name=item.team_score.rating_format.name,
            delta_points=item.delta_points,
            delta_games=item.delta_games,
            reason=item.reason,
            author_name=item.author.get_full_name() or item.author.username,
            id=item.pk,
            can_reverse=item.source != ScoreAdjustment.Source.REVERSAL and not hasattr(item, 'reversal'),
            reversal_form=(
                ReversalForm(initial={'operation_id': uuid.uuid4()})
                if item.source != ScoreAdjustment.Source.REVERSAL and not hasattr(item, 'reversal')
                else None
            ),
        )
        for item in ScoreAdjustment.objects.filter(team_score__team=team)
        .select_related('team_score__rating_format', 'author')[:50]
    ]
    dto = SimpleNamespace(
        id=team.pk,
        name=team.name,
        captain_name=team.captain_name,
        captain=team.captain_name,
        masked_phone=mask_phone(team.phone),
        sms_allowed=team.sms_allowed,
        is_active=team.is_active,
        status='active' if team.is_active else 'archived',
        status_label='Активна' if team.is_active else 'В архиве',
        sms_status_label='Разрешены' if team.sms_allowed else 'Не разрешены',
        private_note=team.private_note,
        comment=team.private_note,
    )
    context = _common(request, city)
    context.update(
        {
            'team': dto,
            'scores': scores,
            'adjustments': adjustments,
            'achievements': achievements,
            'events': RankChangeEvent.objects.filter(team_score__team=team)[:50],
            'deliveries': MessageDelivery.objects.filter(event__team_score__team=team)[:50],
        }
    )
    return render(request, 'rating/admin/team_detail.html', context)


@login_required
@require_POST
def team_archive(request, team_id):
    team, _ = _scoped_team(request, team_id)
    team.is_active = False
    team.archived_at = timezone.now()
    team.save(update_fields=('is_active', 'archived_at', 'updated_at'))
    return redirect('rating_admin:team_list')


def _adjust_preview(score, cleaned):
    points = score.points + cleaned['delta_points']
    games = score.games + cleaned['delta_games']
    if points < 0 or games < 0:
        raise ValidationError('Итоговые значения не могут быть отрицательными')
    ranks = list(score.rating_format.ranks.filter(is_active=True).order_by('min_points', 'level'))
    new_rank = rank_for_points(ranks, points)
    new_achievements = [
        rank for rank in ranks
        if score.points < rank.min_points <= points
        and not TeamRankAchievement.objects.filter(team_score=score, rank=rank).exists()
    ]
    effective_gifts = gifts_for_ranks(
        city_id=score.team.city_id, ranks=new_achievements
    )
    return SimpleNamespace(
        old_points=score.points,
        delta_points=cleaned['delta_points'],
        new_points=points,
        old_games=score.games,
        delta_games=cleaned['delta_games'],
        new_games=games,
        old_rank=score.current_rank,
        new_rank=new_rank,
        new_achievements=new_achievements,
        gift_effect=[
            effective_gifts[rank.pk]
            for rank in new_achievements
            if effective_gifts[rank.pk]
        ],
        sms_effect=(
            cleaned['source'] == ScoreAdjustment.Source.GAME_RESULT
            and bool(new_achievements)
            and new_rank in new_achievements
        ),
        masked_phone=mask_phone(score.team.phone),
    )


@login_required
def score_adjust(request, team_id, format_code):
    score, city = _scoped_score(request, team_id, format_code)
    form = ScoreAdjustmentForm(
        request.POST or None,
        initial={
            'operation_id': uuid.uuid4(),
            'expected_version': score.version,
            'source': ScoreAdjustment.Source.GAME_RESULT,
        },
    )
    preview = None
    if request.method == 'POST' and form.is_valid():
        try:
            preview = _adjust_preview(score, form.cleaned_data)
        except RatingError as exc:
            form.add_error(None, str(exc))
        else:
            payload = {
                'team_id': team_id,
                'format_code': format_code,
                'delta_points': str(form.cleaned_data['delta_points']),
                'delta_games': form.cleaned_data['delta_games'],
                'reason': form.cleaned_data['reason'],
                'source': form.cleaned_data['source'],
                'operation_id': str(form.cleaned_data['operation_id']),
                'expected_version': form.cleaned_data['expected_version'],
            }
            preview.preview_token = signing.dumps(payload, salt='rating-adjust-preview')
    context = _common(request, city)
    context.update(
        {
            'form': form,
            'team': score.team,
            'score': SimpleNamespace(
                points=score.points,
                games=score.games,
                rank_name=score.current_rank.name if score.current_rank else '',
            ),
            'current_format': _format_dto(score.rating_format),
            'preview': preview,
            'is_stale': False,
            'games_form': GamesAdjustmentForm(
                initial={
                    'operation_id': uuid.uuid4(),
                    'delta_games': 1,
                    'expected_version': score.version,
                }
            ),
        }
    )
    return render(request, 'rating/admin/adjustment_form.html', context)


@login_required
@require_POST
def score_adjust_commit(request, team_id, format_code):
    score, city = _scoped_score(request, team_id, format_code)
    form = AdjustmentCommitForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest('Некорректный предпросмотр')
    try:
        payload = signing.loads(
            form.cleaned_data['preview_token'], salt='rating-adjust-preview', max_age=1800
        )
        if payload['team_id'] != team_id or payload['format_code'] != format_code:
            raise signing.BadSignature
        adjustment, _ = apply_adjustment(
            actor=request.user,
            team_score=score,
            delta_points=payload['delta_points'],
            delta_games=payload['delta_games'],
            reason=payload['reason'],
            source=payload['source'],
            operation_id=payload['operation_id'],
            expected_version=payload['expected_version'],
        )
    except signing.BadSignature:
        return HttpResponseBadRequest('Предпросмотр недействителен')
    except RatingError as exc:
        score = TeamScore.objects.select_related('team', 'rating_format', 'current_rank').get(pk=score.pk)
        context = _common(request, city)
        context.update(
            {
                'form': ScoreAdjustmentForm(
                    initial={
                        'operation_id': payload.get('operation_id', uuid.uuid4()),
                        'delta_points': payload.get('delta_points', '0'),
                        'delta_games': payload.get('delta_games', 0),
                        'reason': payload.get('reason', ''),
                        'source': payload.get('source', ScoreAdjustment.Source.GAME_RESULT),
                        'expected_version': score.version,
                    }
                ),
                'team': score.team,
                'score': _score_dto(score),
                'current_format': _format_dto(score.rating_format),
                'preview': None,
                'is_stale': True,
                'games_form': GamesAdjustmentForm(
                    initial={
                        'operation_id': uuid.uuid4(),
                        'delta_games': 1,
                        'expected_version': score.version,
                    }
                ),
            }
        )
        return _domain_error_response(
            request, exc, 'rating/admin/adjustment_form.html', context
        )
    messages.success(request, 'Изменение сохранено')
    return redirect('rating_admin:team_detail', team_id=adjustment.team_score.team_id)


@login_required
@require_POST
def games_adjust(request, team_id, format_code):
    score, _ = _scoped_score(request, team_id, format_code)
    form = GamesAdjustmentForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest('Некорректная корректировка игр')
    try:
        apply_adjustment(
            actor=request.user,
            team_score=score,
            delta_points=Decimal('0'),
            delta_games=form.cleaned_data['delta_games'],
            reason=form.cleaned_data['reason'],
            source=ScoreAdjustment.Source.CORRECTION,
            operation_id=form.cleaned_data['operation_id'],
            expected_version=form.cleaned_data['expected_version'],
        )
    except RatingError as exc:
        return _domain_error_response(request, exc)
    return redirect('rating_admin:team_detail', team_id=team_id)


@login_required
@require_POST
def adjustment_reverse(request, adjustment_id):
    city = _current_city(request)
    adjustment = get_object_or_404(
        ScoreAdjustment.objects.select_related('team_score__team'),
        pk=adjustment_id,
        team_score__team__city=city,
    )
    form = ReversalForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest('Некорректная обратная операция')
    try:
        reversal, _ = reverse_adjustment(actor=request.user, adjustment=adjustment, **form.cleaned_data)
    except RatingError as exc:
        return _domain_error_response(request, exc)
    return redirect('rating_admin:team_detail', team_id=reversal.team_score.team_id)


def _event_context(request, history=False):
    city = _current_city(request)
    queryset = RankChangeEvent.objects.filter(team_score__team__city=city).select_related(
        'team_score__team', 'team_score__rating_format', 'old_rank', 'new_rank'
    )
    format_code = request.GET.get('format', '')
    if format_code:
        queryset = queryset.filter(team_score__rating_format__code=format_code)
    if not history:
        queryset = queryset.filter(
            acknowledged_at__isnull=True,
            direction=RankChangeEvent.Direction.INCREASE,
        )
        direction_filter = RankChangeEvent.Direction.INCREASE
    else:
        direction_filter = request.GET.get('direction', 'all')
        if direction_filter in RankChangeEvent.Direction.values:
            queryset = queryset.filter(direction=direction_filter)
        else:
            direction_filter = 'all'
    source_filter = request.GET.get('source', '')
    normalized_source = (
        RankChangeEvent.Source.CATALOG if source_filter == 'recalculation' else source_filter
    )
    if normalized_source in RankChangeEvent.Source.values:
        queryset = queryset.filter(source=normalized_source)
    else:
        source_filter = ''
    page_obj = Paginator(queryset, 25).get_page(request.GET.get('page'))
    event_rows = []
    for event in page_obj.object_list:
        ack_form = (
            AcknowledgeEventForm(initial={'operation_id': uuid.uuid4()})
            if event.acknowledged_at is None else None
        )
        delivery = event.deliveries.order_by('-created_at').first()
        achievement = event.achievements.exclude(gift_snapshot='').order_by('-rank__level').first()
        event_rows.append(
            SimpleNamespace(
                id=event.pk,
                team_id=event.team_score.team_id,
                team_name=event.team_score.team.name,
                format_name=event.team_score.rating_format.name,
                direction=event.direction,
                direction_label=event.get_direction_display(),
                source_label=event.get_source_display(),
                old_rank_name=event.old_rank_name,
                new_rank_name=event.new_rank_name,
                detected_at=event.detected_at,
                acknowledged_at=event.acknowledged_at,
                acknowledged_by_name=(
                    (event.acknowledged_by.get_full_name() or event.acknowledged_by.username)
                    if event.acknowledged_by else ''
                ),
                gift_label=(achievement.gift_snapshot if achievement else ''),
                delivery_status=(delivery.status if delivery else ''),
                delivery_status_label=(delivery.get_status_display() if delivery else ''),
                ack_form=ack_form,
            )
        )
    page_obj.object_list = event_rows
    formats = list(RatingFormat.objects.filter(is_active=True).order_by('order', 'id'))
    current = next((item for item in formats if item.code == format_code), None)
    context = _common(request, city)
    context.update(
        {
            'page_obj': page_obj,
            'current_format': _format_dto(current) if current else None,
            'direction_filter': direction_filter,
            'source_filter': source_filter,
        }
    )
    return context


@login_required
def event_list(request):
    return render(request, 'rating/admin/event_list.html', _event_context(request))


@login_required
def event_history(request):
    return render(request, 'rating/admin/event_history.html', _event_context(request, history=True))


@login_required
@require_POST
def event_acknowledge(request, event_id):
    city = _current_city(request)
    event = get_object_or_404(
        RankChangeEvent.objects.select_related('team_score__team'),
        pk=event_id,
        team_score__team__city=city,
    )
    form = AcknowledgeEventForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest('Некорректная операция')
    acknowledge_event(actor=request.user, event=event)
    return redirect('rating_admin:event_list')


@login_required
@require_POST
def gift_status(request, achievement_id):
    city = _current_city(request)
    achievement = get_object_or_404(
        TeamRankAchievement.objects.select_related('team_score__team'),
        pk=achievement_id,
        team_score__team__city=city,
    )
    form = GiftStatusForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest('Некорректный статус подарка')
    try:
        update_gift_status(actor=request.user, achievement=achievement, **form.cleaned_data)
    except RatingError as exc:
        return _domain_error_response(request, exc)
    return redirect('rating_admin:team_detail', team_id=achievement.team_score.team_id)


@login_required
def message_incidents(request):
    city = _current_city(request)
    status_filter = request.GET.get('status', '')
    queryset = MessageDelivery.objects.filter(event__team_score__team__city=city).select_related(
        'event__team_score__team', 'event__team_score__rating_format'
    )
    format_code = request.GET.get('format', '')
    if format_code:
        queryset = queryset.filter(event__team_score__rating_format__code=format_code)
    if status_filter in MessageDelivery.Status.values:
        queryset = queryset.filter(status=status_filter)
    else:
        status_filter = 'incidents'
        queryset = queryset.filter(
            status__in=(MessageDelivery.Status.FAILED, MessageDelivery.Status.UNKNOWN)
        )
    page_obj = Paginator(queryset.order_by('-created_at'), 25).get_page(request.GET.get('page'))
    delivery_rows = []
    for delivery in page_obj.object_list:
        retry_form = (
            MessageRetryForm(initial={'operation_id': uuid.uuid4()})
            if delivery.status in (MessageDelivery.Status.FAILED, MessageDelivery.Status.UNKNOWN)
            and delivery.expires_at > timezone.now()
            else None
        )
        delivery_rows.append(
            SimpleNamespace(
                id=delivery.pk,
                team_id=delivery.event.team_score.team_id,
                team_name=delivery.event.team_score.team.name,
                format_name=delivery.event.team_score.rating_format.name,
                rank_name=delivery.event.new_rank_name,
                status=delivery.status,
                status_label=delivery.get_status_display(),
                masked_recipient=mask_phone(delivery.recipient),
                created_at=delivery.created_at,
                attempts=delivery.attempt_count,
                safe_error_label=delivery.safe_error_code,
                can_retry=(
                    delivery.status in (MessageDelivery.Status.FAILED, MessageDelivery.Status.UNKNOWN)
                    and delivery.expires_at > timezone.now()
                ),
                retry_form=retry_form,
            )
        )
    page_obj.object_list = delivery_rows
    context = _common(request, city)
    formats = list(RatingFormat.objects.filter(is_active=True).order_by('order', 'id'))
    current = next((item for item in formats if item.code == format_code), None)
    context.update(
        {
            'page_obj': page_obj,
            'status_filter': status_filter,
            'current_format': _format_dto(current) if current else None,
            'delivery_status_choices': MessageDelivery.Status.choices,
            'bulk_form': BulkMessageForm() if request.user.is_superuser else None,
            'bulk_preview': None,
        }
    )
    return render(request, 'rating/admin/message_incidents.html', context)


@login_required
@require_POST
def message_retry(request, delivery_id):
    city = _current_city(request)
    delivery = get_object_or_404(
        MessageDelivery.objects.select_related('event__team_score__team'),
        pk=delivery_id,
        event__team_score__team__city=city,
    )
    form = MessageRetryForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest('Некорректный повтор')
    try:
        request_manual_retry(actor=request.user, delivery=delivery, **form.cleaned_data)
    except RatingError as exc:
        return _domain_error_response(request, exc)
    return redirect('rating_admin:message_incidents')


def _superuser(request):
    if not request.user.is_authenticated or not request.user.is_active or not request.user.is_superuser:
        raise DjangoPermissionDenied


@login_required
def catalog(request):
    if not request.user.is_superuser:
        if request.method != 'GET':
            raise DjangoPermissionDenied
        city = _current_city(request)
        formats = list(RatingFormat.objects.all().order_by('order', 'id'))
        requested_code = request.GET.get('format', '')
        current_format = next(
            (item for item in formats if item.code == requested_code),
            formats[0] if formats else None,
        )
        ranks = list(
            Rank.objects.filter(rating_format=current_format).order_by('level')
            if current_format
            else Rank.objects.none()
        )
        overrides = {
            item.rank_id: item
            for item in CityRankGift.objects.filter(
                city=city, rank_id__in=[rank.pk for rank in ranks]
            )
        }
        rank_rows = [
            SimpleNamespace(
                rank=rank,
                override=overrides.get(rank.pk),
                effective_gift=(
                    overrides[rank.pk].gift if rank.pk in overrides else rank.gift
                ),
                form=CityRankGiftForm(
                    initial={
                        'gift': overrides[rank.pk].gift if rank.pk in overrides else rank.gift
                    }
                ),
            )
            for rank in ranks
        ]
        context = _common(request, city)
        context.update(
            {
                'formats': formats,
                'current_format': current_format,
                'rank_rows': rank_rows,
            }
        )
        return render(request, 'rating/admin/city_gifts.html', context)

    _superuser(request)
    page_settings = RatingPageSettings.get_solo()
    settings_form = RatingPageSettingsForm(request.POST or None, instance=page_settings)
    if request.method == 'POST' and settings_form.is_valid():
        settings_form.save()
        messages.success(request, 'Тексты и шаблон сохранены')
        return redirect('rating_admin:catalog')
    formats = list(RatingFormat.objects.all().order_by('order', 'id'))
    requested_code = request.GET.get('format', '')
    current_format = next(
        (item for item in formats if item.code == requested_code),
        formats[0] if formats else None,
    )
    rank_queryset = Rank.objects.select_related('rating_format')
    if current_format:
        rank_queryset = rank_queryset.filter(rating_format=current_format)
    else:
        rank_queryset = rank_queryset.none()
    rank_rows = [
        SimpleNamespace(
            id=rank.pk,
            level=rank.level,
            name=rank.name,
            min_points=rank.min_points,
            gift=rank.gift,
            active=rank.is_active,
            logo_url=rank.logo.url if rank.logo else '',
            format_code=rank.rating_format.code,
        )
        for rank in rank_queryset.order_by('level')
    ]
    context = _common(request, _current_city(request, required=False))
    context.update(
        {
            'formats': formats,
            'ranks': rank_rows,
            'current_format': current_format,
            'rank_form': None,
            'rank_preview': None,
            'settings_form': settings_form,
        }
    )
    return render(request, 'rating/admin/settings_catalog.html', context)


@login_required
@require_POST
def city_rank_gift_update(request, rank_id):
    city = _current_city(request)
    rank = get_object_or_404(Rank.objects.select_related('rating_format'), pk=rank_id)
    action = request.POST.get('action', 'save')
    if action == 'inherit':
        clear_city_rank_gift(actor=request.user, city=city, rank=rank)
        messages.success(request, 'Для ранга включен глобальный подарок')
    elif action == 'save':
        form = CityRankGiftForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest('Некорректное описание подарка')
        set_city_rank_gift(
            actor=request.user,
            city=city,
            rank=rank,
            gift=form.cleaned_data['gift'],
        )
        messages.success(request, 'Подарок для города сохранён')
    else:
        return HttpResponseBadRequest('Некорректное действие')
    return redirect('{}?format={}'.format(reverse('rating_admin:catalog'), rank.rating_format.code))


@login_required
def format_edit(request, format_id):
    _superuser(request)
    rating_format = get_object_or_404(RatingFormat, pk=format_id)
    original_is_active = rating_format.is_active
    form = RatingFormatForm(request.POST or None, instance=rating_format)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            rating_format = form.save()
            if not original_is_active and rating_format.is_active:
                existing = set(
                    TeamScore.objects.filter(rating_format=rating_format).values_list(
                        'team_id', flat=True
                    )
                )
                TeamScore.objects.bulk_create(
                    [
                        TeamScore(team_id=team_id, rating_format=rating_format)
                        for team_id in Team.objects.values_list('pk', flat=True)
                        if team_id not in existing
                    ],
                    ignore_conflicts=True,
                )
            RatingFormat.objects.filter(pk=rating_format.pk).update(
                catalog_version=rating_format.catalog_version + 1
            )
        return redirect('rating_admin:catalog')
    context = _common(request, _current_city(request, required=False))
    context.update({'form': form, 'format': rating_format})
    return render(request, 'rating/admin/format_form.html', context)


@login_required
def rank_edit(request, rank_id):
    _superuser(request)
    rank = get_object_or_404(Rank.objects.select_related('rating_format'), pk=rank_id)
    original_min_points = rank.min_points
    original_is_active = rank.is_active
    form = RankForm(request.POST or None, request.FILES or None, instance=rank, lock_format=True)
    preview = None
    if request.method == 'POST' and form.is_valid():
        threshold_changed = (
            form.cleaned_data['min_points'] != original_min_points
            or form.cleaned_data['is_active'] != original_is_active
        )
        if threshold_changed:
            if request.FILES:
                form.add_error('logo', 'Логотип сохраните отдельно от изменения порога')
            else:
                proposed = {
                    'min_points': form.cleaned_data['min_points'],
                    'name': form.cleaned_data['name'],
                    'description': form.cleaned_data['description'],
                    'gift': form.cleaned_data['gift'],
                    'is_active': form.cleaned_data['is_active'],
                    'logo_alt': form.cleaned_data['logo_alt'],
                }
                try:
                    preview = build_rank_preview(actor=request.user, rank=rank, proposed=proposed)
                except RatingError as exc:
                    form.add_error(None, str(exc))
        else:
            form.save()
            RatingFormat.objects.filter(pk=rank.rating_format_id).update(
                catalog_version=rank.rating_format.catalog_version + 1
            )
            return redirect('rating_admin:catalog')
    context = _common(request, _current_city(request, required=False))
    context.update(
        {'rank': rank, 'is_create': False, 'rank_form': form, 'rank_preview': preview}
    )
    return render(request, 'rating/admin/rank_form.html', context)


@login_required
@require_POST
def rank_change_commit(request, rank_id):
    _superuser(request)
    token = request.POST.get('preview_token', '')
    try:
        payload = signing.loads(token, salt='rating-rank-preview', max_age=1800)
        if payload.get('rank_id') != rank_id:
            raise signing.BadSignature
        commit_rank_preview(actor=request.user, token=token)
    except signing.BadSignature:
        return HttpResponseBadRequest('Некорректный предпросмотр')
    except RatingError as exc:
        return _domain_error_response(request, exc)
    return redirect('rating_admin:catalog')


@login_required
def rank_create(request):
    _superuser(request)
    form = RankForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        rating_format = form.cleaned_data['rating_format']
        try:
            with transaction.atomic():
                locked_format = RatingFormat.objects.select_for_update().get(pk=rating_format.pk)
                rank = form.save()
                thresholds = list(
                    Rank.objects.filter(rating_format=rating_format, is_active=True)
                    .order_by('level').values_list('min_points', flat=True)
                )
                if thresholds != sorted(thresholds) or len(thresholds) != len(set(thresholds)):
                    raise ValidationError('Пороги должны строго возрастать по уровню')
                recalculate_format_scores(locked_format)
                RatingFormat.objects.filter(pk=rating_format.pk).update(
                    catalog_version=locked_format.catalog_version + 1
                )
        except RatingError as exc:
            form.add_error('min_points', str(exc))
        if not form.errors:
            return redirect('rating_admin:catalog')
    context = _common(request, _current_city(request, required=False))
    context.update({'rank': None, 'is_create': True, 'rank_form': form, 'rank_preview': None})
    return render(request, 'rating/admin/rank_form.html', context)


@login_required
def integration_settings(request):
    _superuser(request)
    instance = SmsIntegrationSettings.get_solo()
    env_override = bool(os.environ.get('SMSPILOT_API_KEY'))
    form = SmsIntegrationSettingsForm(request.POST or None, instance=instance)
    if env_override:
        form.fields['api_key'].disabled = True
        form.fields['clear_api_key'].disabled = True
        form.fields['api_key'].help_text = 'Активный ключ задан окружением и не меняется из браузера.'
    if request.method == 'POST' and form.is_valid():
        if env_override and (form.cleaned_data.get('api_key') or form.cleaned_data.get('clear_api_key')):
            form.add_error(None, 'Активный ключ задан окружением; web-замена недоступна')
        else:
            try:
                instance = form.save(commit=False)
                if form.cleaned_data.get('clear_api_key'):
                    instance.api_key_ciphertext = ''
                    instance.api_key_updated_at = timezone.now()
                    instance.api_key_updated_by = request.user
                elif form.cleaned_data.get('api_key'):
                    instance.api_key_ciphertext = encrypt_secret(form.cleaned_data['api_key'])
                    instance.api_key_updated_at = timezone.now()
                    instance.api_key_updated_by = request.user
                instance.save()
            except Exception:
                form.add_error(None, 'Хранилище секретов не настроено')
            else:
                return redirect('rating_admin:integration_settings')
    safe_errors = [
        SimpleNamespace(created_at=item.updated_at, label=item.safe_error_code)
        for item in MessageDelivery.objects.exclude(safe_error_code='').order_by('-updated_at')[:10]
    ]
    context = _common(request, _current_city(request, required=False))
    context.update(
        {
            'integration_form': form,
            'key_configured': env_override or bool(instance.api_key_ciphertext),
            'key_source': 'environment' if env_override else (
                'encrypted_store' if instance.api_key_ciphertext else 'none'
            ),
            'key_web_mutable': not env_override,
            'sending_enabled': instance.sending_enabled,
            'emergency_stop': instance.emergency_stop,
            'last_safe_errors': safe_errors,
        }
    )
    return render(request, 'rating/admin/integration_settings.html', context)


@login_required
@require_POST
def integration_test_send(request):
    _superuser(request)
    integration = SmsIntegrationSettings.get_solo()
    if integration.emergency_stop:
        messages.error(request, 'Тестовая отправка заблокирована аварийной остановкой')
        return redirect('rating_admin:integration_settings')
    if not integration.test_phone:
        return HttpResponseBadRequest('Сначала сохраните тестовый номер')
    result = SmsPilotClient().send(
        SimpleNamespace(
            recipient=integration.test_phone,
            rendered_body='Тестовое сообщение рейтинга. Отправка в режиме test=1.',
        ),
        sender_name=integration.sender_name,
        test_mode=True,
    )
    if result.status in (MessageDelivery.Status.FAILED, MessageDelivery.Status.UNKNOWN):
        messages.error(request, 'Тест не подтверждён: {}'.format(result.safe_error_code or result.status))
    else:
        messages.success(request, 'Тестовый запрос принят: {}'.format(result.status))
    return redirect('rating_admin:integration_settings')


def _bulk_candidates(statuses):
    return MessageDelivery.objects.filter(
        status__in=statuses, expires_at__gt=timezone.now()
    ).order_by('pk')


@login_required
def bulk_message_preview(request):
    _superuser(request)
    form = BulkMessageForm(request.POST or None)
    preview = None
    if request.method == 'POST' and form.is_valid():
        statuses = form.cleaned_data['statuses']
        if 'unknown' in statuses and not form.cleaned_data['confirm_unknown']:
            form.add_error('confirm_unknown', 'Подтвердите риск unknown')
        else:
            rows = list(
                _bulk_candidates(statuses).values_list('pk', 'status', 'updated_at', 'parts')
            )
            digest = hashlib.sha256(repr(rows).encode('utf-8')).hexdigest()
            token = signing.dumps(
                {
                    'statuses': statuses,
                    'digest': digest,
                    'operation_id': str(form.cleaned_data['operation_id']),
                    'reason': form.cleaned_data['reason'],
                },
                salt='rating-bulk-preview',
            )
            preview = SimpleNamespace(
                count=len(rows),
                parts=sum((row[3] or 1) for row in rows),
                cost_estimate=None,
                preview_token=token,
            )
    context = _common(request, _current_city(request, required=False))
    context.update({'bulk_form': form, 'bulk_preview': preview})
    return render(request, 'rating/admin/bulk_message_preview.html', context)


@login_required
@require_POST
def bulk_message_commit(request):
    _superuser(request)
    form = BulkCommitForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest('Некорректное подтверждение')
    try:
        payload = signing.loads(
            form.cleaned_data['preview_token'], salt='rating-bulk-preview', max_age=900
        )
    except signing.BadSignature:
        return HttpResponseBadRequest('Предпросмотр устарел')
    try:
        with transaction.atomic():
            rows = list(
                _bulk_candidates(payload['statuses'])
                .select_for_update()
                .values_list('pk', 'status', 'updated_at', 'parts')
            )
            if hashlib.sha256(repr(rows).encode('utf-8')).hexdigest() != payload['digest']:
                raise ConcurrencyConflict('Состав отправок изменился')
            parent_operation_id = uuid.UUID(payload['operation_id'])
            now = timezone.now()
            for delivery_id, observed_status, observed_updated_at, _ in rows:
                child_operation_id = uuid.uuid5(parent_operation_id, str(delivery_id))
                MessageAttempt.objects.create(
                    operation_id=child_operation_id,
                    delivery_id=delivery_id,
                    kind=MessageAttempt.Kind.MANUAL,
                    result_status=MessageDelivery.Status.QUEUED,
                    safe_error_code='bulk_retry_requested',
                    reason=payload['reason'],
                    actor=request.user,
                )
                changed = MessageDelivery.objects.filter(
                    pk=delivery_id,
                    status=observed_status,
                    updated_at=observed_updated_at,
                ).update(
                    status=MessageDelivery.Status.QUEUED,
                    safe_error_code='',
                    next_attempt_at=now,
                    lease_token=None,
                    lease_until=None,
                )
                if changed != 1:
                    raise ConcurrencyConflict('Статус отправки изменился')
    except (ConcurrencyConflict, ValueError, KeyError) as exc:
        return _domain_error_response(request, ConcurrencyConflict(str(exc)))
    return redirect('rating_admin:message_incidents')
