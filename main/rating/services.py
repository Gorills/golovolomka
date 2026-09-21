import hashlib
import json
import re
import unicodedata
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from string import Formatter

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import (
    CityRatingAccess,
    CityRankGift,
    GiftStatusChange,
    MessageAttempt,
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


ALLOWED_SMS_PLACEHOLDERS = frozenset(
    {'team', 'city', 'format', 'old_rank', 'new_rank', 'points', 'gift', 'rating_url'}
)
POINTS_QUANTUM = Decimal('0.1')
User = get_user_model()


class RatingError(Exception):
    code = 'rating_error'


class PermissionDenied(RatingError):
    code = 'permission_denied'


class ValidationError(RatingError):
    code = 'validation_error'


class IdempotencyConflict(RatingError):
    code = 'idempotency_conflict'


class ConcurrencyConflict(RatingError):
    code = 'concurrency_conflict'


class StalePreview(RatingError):
    code = 'stale_preview'


def require_global_admin(user):
    if (
        not user
        or not user.is_authenticated
        or not user.is_active
        or not user.is_superuser
    ):
        raise PermissionDenied()


def _validate_city_operator(account):
    if not account.is_active or account.is_staff or account.is_superuser:
        raise ValidationError('Доступ можно назначить только активному обычному пользователю')


def create_city_operator(*, actor, username, email, password, city):
    require_global_admin(actor)
    with transaction.atomic():
        account = User(
            username=username,
            email=email,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        account.full_clean(exclude=('password',))
        account.set_password(password)
        account.save()
        access = CityRatingAccess.objects.create(
            user=account,
            city=city,
            role=CityRatingAccess.Role.OPERATOR,
            is_active=True,
        )
    return account, access


def grant_city_access(*, actor, account, city):
    require_global_admin(actor)
    with transaction.atomic():
        account = User.objects.select_for_update().get(pk=account.pk)
        _validate_city_operator(account)
        access, created = CityRatingAccess.objects.select_for_update().get_or_create(
            user=account,
            city=city,
            defaults={
                'role': CityRatingAccess.Role.OPERATOR,
                'is_active': True,
            },
        )
        reactivated = False
        if not created and not access.is_active:
            access.is_active = True
            access.role = CityRatingAccess.Role.OPERATOR
            access.save(update_fields=('is_active', 'role'))
            reactivated = True
    return access, created, reactivated


def revoke_city_access(*, actor, access):
    require_global_admin(actor)
    with transaction.atomic():
        access = CityRatingAccess.objects.select_for_update().get(pk=access.pk)
        changed = access.is_active
        if changed:
            access.is_active = False
            access.save(update_fields=('is_active',))
    return access, changed


def normalize_team_name(value):
    value = unicodedata.normalize('NFKC', str(value or ''))
    return ' '.join(value.split()).casefold()


def canonical_phone(value):
    raw = str(value or '').strip()
    if not raw:
        return ''
    if not re.fullmatch(r'[+\d\s()\-]+', raw):
        raise ValidationError('Некорректный номер телефона')
    digits = re.sub(r'\D', '', raw)
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    if not 7 <= len(digits) <= 15:
        raise ValidationError('Номер должен содержать от 7 до 15 цифр')
    return '+' + digits


def mask_phone(value):
    digits = re.sub(r'\D', '', value or '')
    if len(digits) < 4:
        return '—' if not digits else '*' * len(digits)
    return '+{}•••{}'.format(digits[:1], digits[-4:])


def parse_points(value):
    text = str(value).strip().replace(',', '.')
    try:
        parsed = Decimal(text)
    except (InvalidOperation, ValueError):
        raise ValidationError('Баллы должны быть десятичным числом')
    if not parsed.is_finite() or parsed.as_tuple().exponent < -1:
        raise ValidationError('Баллы вводятся с точностью до десятых без округления')
    return parsed.quantize(POINTS_QUANTUM)


def require_city_access(user, city_id):
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied()
    if user.is_superuser:
        return None
    try:
        return CityRatingAccess.objects.get(user=user, city_id=city_id, is_active=True)
    except CityRatingAccess.DoesNotExist:
        raise PermissionDenied()


def rank_for_points(ranks, points):
    current = None
    for rank in ranks:
        if Decimal(rank.min_points) <= points:
            current = rank
        else:
            break
    return current


def rank_for_threshold_pairs(pairs, points):
    current = None
    for min_points, rank in sorted(pairs, key=lambda pair: (pair[0], pair[1].level)):
        if Decimal(min_points) <= points:
            current = rank
        else:
            break
    return current


def gifts_for_ranks(*, city_id, ranks):
    ranks = list(ranks)
    gifts = {rank.pk: rank.gift for rank in ranks}
    if not ranks:
        return gifts
    overrides = CityRankGift.objects.filter(
        city_id=city_id, rank_id__in=gifts
    ).values_list('rank_id', 'gift')
    gifts.update(overrides)
    return gifts


def set_city_rank_gift(*, actor, city, rank, gift):
    require_city_access(actor, city.pk)
    with transaction.atomic():
        override, _ = CityRankGift.objects.update_or_create(
            city=city,
            rank=rank,
            defaults={'gift': (gift or '').strip(), 'updated_by': actor},
        )
    return override


def clear_city_rank_gift(*, actor, city, rank):
    require_city_access(actor, city.pk)
    CityRankGift.objects.filter(city=city, rank=rank).delete()


def _rank_snapshot(rank):
    return (rank.level, rank.name) if rank else (None, '')


def _payload_hash(score_id, delta_points, delta_games, reason, source, reverses_id=None):
    payload = {
        'score_id': score_id,
        'delta_points': str(delta_points),
        'delta_games': int(delta_games),
        'reason': reason.strip(),
        'source': source,
        'reverses_id': reverses_id,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def validate_sms_template(template):
    fields = set()
    try:
        parsed = list(Formatter().parse(template or ''))
        for _, field_name, format_spec, conversion in parsed:
            if field_name:
                fields.add(field_name)
            if format_spec or conversion:
                raise ValidationError('Форматирование и преобразования плейсхолдеров запрещены')
    except ValueError:
        raise ValidationError('Некорректные фигурные скобки в шаблоне')
    unknown = fields - ALLOWED_SMS_PLACEHOLDERS
    if unknown:
        raise ValidationError('Недопустимые плейсхолдеры: {}'.format(', '.join(sorted(unknown))))
    if template and 'rating_url' not in fields:
        raise ValidationError('Шаблон должен содержать {rating_url}')
    if template:
        try:
            template.format(**{field: 'test' for field in ALLOWED_SMS_PLACEHOLDERS})
        except (KeyError, ValueError, AttributeError, IndexError):
            raise ValidationError('Шаблон сообщения не может быть отформатирован')


def _render_sms(event, achievement, points):
    template = RatingPageSettings.get_solo().sms_template
    if not template:
        return ''
    validate_sms_template(template)
    score = event.team_score
    values = {
        'team': score.team.name,
        'city': score.team.city.name,
        'format': score.rating_format.name,
        'old_rank': event.old_rank_name or 'Без ранга',
        'new_rank': event.new_rank_name or 'Без ранга',
        'points': str(points).replace('.', ','),
        'gift': achievement.gift_snapshot if achievement else '',
        'rating_url': getattr(
            settings,
            'RATING_PUBLIC_URL_TEMPLATE',
            'https://{city}.golovolomka.fun/rating/',
        ).format(city=score.team.city.slug),
    }
    return template.format(**values)


def sms_parts(body):
    if not body:
        return 0
    cyrillic = any(ord(char) > 127 for char in body)
    one, multipart = (70, 67) if cyrillic else (160, 153)
    if len(body) <= one:
        return 1
    return (len(body) + multipart - 1) // multipart


def create_team(*, actor, city, name, captain_name='', phone='', sms_allowed=False,
                consent_source='', consent_recorded_at=None, private_note=''):
    require_city_access(actor, city.pk)
    normalized = normalize_team_name(name)
    if not normalized:
        raise ValidationError('Название команды обязательно')
    canonical = canonical_phone(phone)
    if sms_allowed and (not canonical or not consent_source.strip() or not consent_recorded_at):
        raise ValidationError('Для SMS нужны телефон, источник и дата согласия')
    with transaction.atomic():
        team = Team.objects.create(
            city=city,
            name=' '.join(unicodedata.normalize('NFKC', name).split()),
            normalized_name=normalized,
            captain_name=captain_name.strip(),
            phone=canonical,
            sms_allowed=bool(sms_allowed),
            consent_source=consent_source.strip(),
            consent_recorded_at=consent_recorded_at,
            consent_recorded_by=actor if sms_allowed else None,
            private_note=private_note.strip(),
        )
        formats = list(RatingFormat.objects.all().order_by('order', 'id'))
        TeamScore.objects.bulk_create(
            [TeamScore(team=team, rating_format=rating_format) for rating_format in formats]
        )
    return team


def update_team(*, actor, team, **values):
    require_city_access(actor, team.city_id)
    name = values.get('name', team.name)
    normalized = normalize_team_name(name)
    if not normalized:
        raise ValidationError('Название команды обязательно')
    phone = canonical_phone(values.get('phone', team.phone))
    phone_changed = phone != team.phone
    sms_allowed = bool(values.get('sms_allowed', team.sms_allowed))
    consent_source = values.get('consent_source', team.consent_source).strip()
    consent_at = values.get('consent_recorded_at', team.consent_recorded_at)
    if sms_allowed and (not phone or not consent_source or not consent_at):
        raise ValidationError('Для SMS нужны телефон, источник и дата согласия')
    if phone_changed and sms_allowed and consent_at == team.consent_recorded_at:
        raise ValidationError('Для нового номера заново зафиксируйте дату согласия')
    if phone_changed and not sms_allowed:
        consent_source = ''
        consent_at = None
    team.name = ' '.join(unicodedata.normalize('NFKC', name).split())
    team.normalized_name = normalized
    team.captain_name = values.get('captain_name', team.captain_name).strip()
    team.phone = phone
    team.sms_allowed = sms_allowed
    team.consent_source = consent_source
    team.consent_recorded_at = consent_at
    team.consent_recorded_by = actor if sms_allowed else None
    team.private_note = values.get('private_note', team.private_note).strip()
    team.save()
    return team


def _existing_adjustment(actor, operation_id, score, payload_hash):
    try:
        existing = ScoreAdjustment.objects.select_related('team_score__team').get(
            operation_id=operation_id
        )
    except ScoreAdjustment.DoesNotExist:
        return None
    require_city_access(actor, score.team.city_id)
    if existing.team_score_id != score.pk or existing.payload_hash != payload_hash:
        raise IdempotencyConflict('Ключ операции уже использован для других данных')
    return existing


def apply_adjustment(*, actor, team_score, delta_points, delta_games, reason, source,
                     operation_id, reverses=None, expected_version=None):
    require_city_access(actor, team_score.team.city_id)
    delta_points = parse_points(delta_points)
    try:
        delta_games = int(delta_games)
    except (TypeError, ValueError):
        raise ValidationError('Количество игр должно быть целым числом')
    reason = (reason or '').strip()
    if not reason:
        raise ValidationError('Укажите основание операции')
    if source not in ScoreAdjustment.Source.values:
        raise ValidationError('Некорректный источник операции')
    if source == ScoreAdjustment.Source.REVERSAL and reverses is None:
        raise ValidationError('Обратная операция создаётся только из исходной записи')
    if source != ScoreAdjustment.Source.REVERSAL and reverses is not None:
        raise ValidationError('Связь обратной операции допустима только для reversal')
    if delta_points == 0 and delta_games == 0:
        raise ValidationError('Укажите изменение баллов или игр')
    try:
        operation_id = uuid.UUID(str(operation_id))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError('Некорректный ключ операции')
    payload_hash = _payload_hash(
        team_score.pk, delta_points, delta_games, reason, source, reverses.pk if reverses else None
    )

    with transaction.atomic():
        score = TeamScore.objects.select_related(
            'team__city', 'rating_format', 'current_rank'
        ).get(pk=team_score.pk)
        existing = _existing_adjustment(actor, operation_id, score, payload_hash)
        if existing:
            return existing, False
        if expected_version is not None and score.version != int(expected_version):
            raise ConcurrencyConflict('Данные изменились после предпросмотра')
        points_after = score.points + delta_points
        games_after = score.games + delta_games
        if points_after < 0:
            raise ValidationError('Баллы не могут стать отрицательными')
        if games_after < 0:
            raise ValidationError('Количество игр не может стать отрицательным')
        ranks = list(
            Rank.objects.filter(rating_format=score.rating_format, is_active=True)
            .order_by('min_points', 'level')
        )
        new_rank = rank_for_points(ranks, points_after)
        updated = TeamScore.objects.filter(pk=score.pk, version=score.version).update(
            points=points_after,
            games=games_after,
            current_rank=new_rank,
            version=F('version') + 1,
            updated_at=timezone.now(),
        )
        if updated != 1:
            raise ConcurrencyConflict('Параллельное изменение статистики')
        before_level, before_name = _rank_snapshot(score.current_rank)
        after_level, after_name = _rank_snapshot(new_rank)
        adjustment = ScoreAdjustment.objects.create(
            operation_id=operation_id,
            payload_hash=payload_hash,
            team_score=score,
            delta_points=delta_points,
            delta_games=delta_games,
            reason=reason,
            source=source,
            author=actor,
            points_before=score.points,
            points_after=points_after,
            games_before=score.games,
            games_after=games_after,
            rank_before_level=before_level,
            rank_before_name=before_name,
            rank_after_level=after_level,
            rank_after_name=after_name,
            reverses=reverses,
        )
        if (score.current_rank_id or None) == (new_rank.pk if new_rank else None):
            return adjustment, True
        direction = (
            RankChangeEvent.Direction.INCREASE
            if (after_level or 0) > (before_level or 0)
            else RankChangeEvent.Direction.DECREASE
        )
        event = RankChangeEvent.objects.create(
            team_score=score,
            source_adjustment=adjustment,
            source=RankChangeEvent.Source.ADJUSTMENT,
            direction=direction,
            old_rank=score.current_rank,
            new_rank=new_rank,
            old_rank_level=before_level,
            old_rank_name=before_name,
            new_rank_level=after_level,
            new_rank_name=after_name,
        )
        created_final = None
        if direction == RankChangeEvent.Direction.INCREASE:
            crossed = [rank for rank in ranks if score.points < rank.min_points <= points_after]
            effective_gifts = gifts_for_ranks(city_id=score.team.city_id, ranks=crossed)
            for rank in crossed:
                gift = effective_gifts[rank.pk]
                achievement, created = TeamRankAchievement.objects.get_or_create(
                    team_score=score,
                    rank=rank,
                    defaults={
                        'source_event': event,
                        'rank_name_snapshot': rank.name,
                        'gift_snapshot': gift,
                        'gift_status': (
                            TeamRankAchievement.GiftStatus.PENDING if gift else ''
                        ),
                    },
                )
                if created and new_rank and rank.pk == new_rank.pk:
                    created_final = achievement
        if (
            direction == RankChangeEvent.Direction.INCREASE
            and source == ScoreAdjustment.Source.GAME_RESULT
            and created_final is not None
        ):
            expires = event.detected_at + timedelta(days=3)
            try:
                body = _render_sms(event, created_final, points_after)
                render_error = ''
            except (ValidationError, ValueError, KeyError, AttributeError, IndexError):
                body = ''
                render_error = 'template_render_error'
            if not score.team.phone:
                status, error = MessageDelivery.Status.SKIPPED, 'missing_phone'
            elif not score.team.sms_allowed:
                status, error = MessageDelivery.Status.SKIPPED, 'consent_missing'
            elif render_error:
                status, error = MessageDelivery.Status.FAILED, render_error
            elif not body:
                status, error = MessageDelivery.Status.FAILED, 'template_missing'
            else:
                status, error = MessageDelivery.Status.QUEUED, ''
            MessageDelivery.objects.create(
                event=event,
                recipient=score.team.phone,
                rendered_body=body,
                status=status,
                safe_error_code=error,
                parts=sms_parts(body) or None,
                expires_at=expires,
                next_attempt_at=event.detected_at,
            )
        return adjustment, True


def reverse_adjustment(*, actor, adjustment, operation_id, reason):
    require_city_access(actor, adjustment.team_score.team.city_id)
    if adjustment.source == ScoreAdjustment.Source.REVERSAL:
        raise ValidationError('Обратную операцию нельзя отменить повторно')
    if hasattr(adjustment, 'reversal'):
        return adjustment.reversal, False
    return apply_adjustment(
        actor=actor,
        team_score=adjustment.team_score,
        delta_points=-adjustment.delta_points,
        delta_games=-adjustment.delta_games,
        reason=reason,
        source=ScoreAdjustment.Source.REVERSAL,
        operation_id=operation_id,
        reverses=adjustment,
    )


def acknowledge_event(*, actor, event):
    require_city_access(actor, event.team_score.team.city_id)
    now = timezone.now()
    RankChangeEvent.objects.filter(pk=event.pk, acknowledged_at__isnull=True).update(
        acknowledged_at=now, acknowledged_by=actor
    )
    event.refresh_from_db(fields=('acknowledged_at', 'acknowledged_by'))
    return event


def update_gift_status(*, actor, achievement, status, comment, operation_id):
    require_city_access(actor, achievement.team_score.team.city_id)
    if not achievement.gift_snapshot:
        raise ValidationError('Для этого ранга подарок не предусмотрен')
    if status not in TeamRankAchievement.GiftStatus.values:
        raise ValidationError('Некорректный статус подарка')
    try:
        operation_id = uuid.UUID(str(operation_id))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError('Некорректный ключ операции')
    existing = GiftStatusChange.objects.filter(operation_id=operation_id).first()
    if existing:
        if existing.achievement_id != achievement.pk or existing.new_status != status:
            raise IdempotencyConflict()
        return existing, False
    with transaction.atomic():
        achievement = TeamRankAchievement.objects.select_for_update().get(pk=achievement.pk)
        change = GiftStatusChange.objects.create(
            operation_id=operation_id,
            achievement=achievement,
            old_status=achievement.gift_status,
            new_status=status,
            comment=(comment or '').strip(),
            author=actor,
        )
        achievement.gift_status = status
        achievement.gift_comment = change.comment
        achievement.gift_updated_at = timezone.now()
        achievement.gift_updated_by = actor
        achievement.save(
            update_fields=('gift_status', 'gift_comment', 'gift_updated_at', 'gift_updated_by')
        )
    return change, True


def request_manual_retry(*, actor, delivery, operation_id, reason, confirm_unknown=False):
    require_city_access(actor, delivery.event.team_score.team.city_id)
    now = timezone.now()
    try:
        operation_id = uuid.UUID(str(operation_id))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError('Некорректный ключ операции')
    existing = MessageAttempt.objects.filter(operation_id=operation_id).first()
    if existing:
        if existing.delivery_id != delivery.pk:
            raise IdempotencyConflict()
        return existing, False
    with transaction.atomic():
        delivery = MessageDelivery.objects.select_for_update().select_related(
            'event__team_score__team'
        ).get(pk=delivery.pk)
        if now >= delivery.expires_at:
            raise ValidationError('Срок повторной отправки истёк')
        if delivery.status not in (MessageDelivery.Status.FAILED, MessageDelivery.Status.UNKNOWN):
            raise ConcurrencyConflict('Статус отправки уже изменился')
        if delivery.status == MessageDelivery.Status.UNKNOWN and not confirm_unknown:
            raise ValidationError('Подтвердите риск повторной отправки')
        if not delivery.rendered_body:
            final_achievement = delivery.event.achievements.filter(
                rank_id=delivery.event.new_rank_id
            ).first()
            body = _render_sms(
                delivery.event,
                final_achievement,
                delivery.event.team_score.points,
            )
            if not body:
                raise ValidationError('Сначала настройте утверждённый шаблон SMS')
            delivery.rendered_body = body
            delivery.parts = sms_parts(body)
        attempt = MessageAttempt.objects.create(
            operation_id=operation_id,
            delivery=delivery,
            kind=MessageAttempt.Kind.MANUAL,
            result_status=MessageDelivery.Status.QUEUED,
            safe_error_code='manual_retry_requested',
            reason=(reason or '').strip(),
            actor=actor,
        )
        delivery.status = MessageDelivery.Status.QUEUED
        delivery.safe_error_code = ''
        delivery.next_attempt_at = now
        delivery.lease_token = None
        delivery.lease_until = None
        delivery.save(
            update_fields=(
                'rendered_body', 'parts', 'status', 'safe_error_code', 'next_attempt_at',
                'lease_token', 'lease_until', 'updated_at',
            )
        )
    return attempt, True


def catalog_digest(rating_format):
    rows = list(
        TeamScore.objects.filter(rating_format=rating_format)
        .order_by('pk')
        .values_list('pk', 'version', 'points', 'current_rank_id')
    )
    raw = json.dumps([(pk, version, str(points), rank_id) for pk, version, points, rank_id in rows])
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def build_rank_preview(*, actor, rank, proposed):
    if not actor.is_authenticated or not actor.is_active or not actor.is_superuser:
        raise PermissionDenied()
    proposed_points = int(proposed['min_points'])
    ranks = list(rank.rating_format.ranks.all().order_by('min_points', 'level'))
    affected = []
    for score in TeamScore.objects.filter(rating_format=rank.rating_format).select_related(
        'team__city', 'current_rank'
    ):
        virtual = []
        for item in ranks:
            item_active = (
                bool(proposed.get('is_active')) if item.pk == rank.pk else item.is_active
            )
            if not item_active:
                continue
            item_points = proposed_points if item.pk == rank.pk else item.min_points
            virtual.append((item_points, item))
        new_rank = rank_for_threshold_pairs(virtual, score.points)
        if (score.current_rank_id or None) != (new_rank.pk if new_rank else None):
            old_rank_name = score.current_rank.name if score.current_rank else 'Без ранга'
            new_rank_name = new_rank.name if new_rank else 'Без ранга'
            affected.append(
                {
                    'score_id': score.pk,
                    'team_name': score.team.name,
                    'city_name': score.team.city.name,
                    'old_rank_name': old_rank_name,
                    'new_rank_name': new_rank_name,
                    'team': score.team.name,
                    'city': score.team.city.name,
                    'old_rank': old_rank_name,
                    'new_rank': new_rank_name,
                }
            )
    payload = {
        'rank_id': rank.pk,
        'format_version': rank.rating_format.catalog_version,
        'digest': catalog_digest(rank.rating_format),
        'proposal': proposed,
    }
    token = signing.dumps(payload, salt='rating-rank-preview', compress=True)
    by_city = {}
    for row in affected:
        by_city[row['city_name']] = by_city.get(row['city_name'], 0) + 1
    return {
        'affected_count': len(affected),
        'affected_rows': affected,
        'by_city': [
            {'city_name': city_name, 'count': count}
            for city_name, count in sorted(by_city.items())
        ],
        'suppressed_actions': 'SMS и подарки подавлены',
        'preview_token': token,
    }


def commit_rank_preview(*, actor, token):
    if not actor.is_authenticated or not actor.is_active or not actor.is_superuser:
        raise PermissionDenied()
    try:
        payload = signing.loads(token, salt='rating-rank-preview', max_age=1800)
    except signing.BadSignature:
        raise StalePreview('Предпросмотр недействителен или устарел')
    with transaction.atomic():
        rank = Rank.objects.select_related('rating_format').get(pk=payload['rank_id'])
        rating_format = RatingFormat.objects.select_for_update().get(pk=rank.rating_format_id)
        if rating_format.catalog_version != payload['format_version']:
            raise StalePreview('Каталог изменился после предпросмотра')
        if catalog_digest(rating_format) != payload['digest']:
            raise StalePreview('Статистика изменилась после предпросмотра')
        proposal = payload['proposal']
        rank.min_points = int(proposal['min_points'])
        rank.name = proposal.get('name', rank.name).strip()
        rank.description = proposal.get('description', rank.description)
        rank.gift = proposal.get('gift', rank.gift)
        rank.is_active = bool(proposal.get('is_active', rank.is_active))
        rank.logo_alt = proposal.get('logo_alt', rank.logo_alt)
        rank.save()
        thresholds = list(
            Rank.objects.filter(rating_format=rating_format, is_active=True)
            .order_by('level')
            .values_list('min_points', flat=True)
        )
        if thresholds != sorted(thresholds) or len(thresholds) != len(set(thresholds)):
            raise ValidationError('Пороги должны строго возрастать по уровню')
        operation_id = uuid.uuid4()
        recalculate_format_scores(rating_format, operation_id)
        rating_format.catalog_version = F('catalog_version') + 1
        rating_format.save(update_fields=('catalog_version',))
    return operation_id


def recalculate_format_scores(rating_format, operation_id=None):
    operation_id = operation_id or uuid.uuid4()
    ranks = list(
        Rank.objects.filter(rating_format=rating_format, is_active=True)
        .order_by('min_points', 'level')
    )
    scores = TeamScore.objects.filter(rating_format=rating_format).select_related('current_rank')
    changed = 0
    for score in scores.order_by('pk'):
        new_rank = rank_for_points(ranks, score.points)
        if (score.current_rank_id or None) == (new_rank.pk if new_rank else None):
            continue
        old_level, old_name = _rank_snapshot(score.current_rank)
        new_level, new_name = _rank_snapshot(new_rank)
        RankChangeEvent.objects.create(
            team_score=score,
            catalog_operation_id=operation_id,
            source=RankChangeEvent.Source.CATALOG,
            direction=(
                RankChangeEvent.Direction.INCREASE
                if (new_level or 0) > (old_level or 0)
                else RankChangeEvent.Direction.DECREASE
            ),
            old_rank=score.current_rank,
            new_rank=new_rank,
            old_rank_level=old_level,
            old_rank_name=old_name,
            new_rank_level=new_level,
            new_rank_name=new_name,
        )
        updated = TeamScore.objects.filter(pk=score.pk, version=score.version).update(
            current_rank=new_rank, version=F('version') + 1, updated_at=timezone.now()
        )
        if updated != 1:
            raise ConcurrencyConflict('Статистика изменилась во время пересчёта')
        changed += 1
    return changed
