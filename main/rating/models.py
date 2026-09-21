import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from home.models import City
from .uploads import rank_logo_path, validate_rank_logo


class CityRatingAccess(models.Model):
    class Role(models.TextChoices):
        OPERATOR = 'operator', 'Оператор'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='rating_accesses'
    )
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='rating_accesses')
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.OPERATOR)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('user', 'city'), name='rating_access_user_city_uniq'),
        ]
        indexes = [models.Index(fields=('user', 'is_active'), name='rating_access_user_active_idx')]


class RatingFormat(models.Model):
    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    catalog_version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ('order', 'id')

    def __str__(self):
        return self.name


class Rank(models.Model):
    rating_format = models.ForeignKey(
        RatingFormat, on_delete=models.PROTECT, related_name='ranks'
    )
    level = models.PositiveSmallIntegerField()
    min_points = models.PositiveIntegerField()
    name = models.CharField(max_length=150)
    logo = models.ImageField(
        upload_to=rank_logo_path, validators=[validate_rank_logo], blank=True, null=True
    )
    logo_alt = models.CharField(max_length=250, blank=True)
    description = models.TextField(blank=True)
    gift = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('rating_format__order', 'level')
        constraints = [
            models.UniqueConstraint(
                fields=('rating_format', 'level'), name='rating_rank_format_level_uniq'
            ),
            models.UniqueConstraint(
                fields=('rating_format', 'min_points'), name='rating_rank_format_points_uniq'
            ),
            models.CheckConstraint(check=models.Q(level__gt=0), name='rating_rank_level_gt_zero'),
            models.CheckConstraint(check=models.Q(min_points__gte=0), name='rating_rank_points_nonnegative'),
        ]
        indexes = [
            models.Index(
                fields=('rating_format', 'is_active', 'min_points'),
                name='rating_rank_lookup_idx',
            )
        ]

    def __str__(self):
        return '{}: {}'.format(self.rating_format.code, self.name)

    def clean(self):
        super().clean()
        if self.logo and not self.logo_alt.strip():
            from django.core.exceptions import ValidationError

            raise ValidationError({'logo_alt': 'Для логотипа нужен альтернативный текст'})


class CityRankGift(models.Model):
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='rating_rank_gifts')
    rank = models.ForeignKey(Rank, on_delete=models.PROTECT, related_name='city_gifts')
    gift = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='updated_city_rating_gifts',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('city', 'rank'), name='rating_city_rank_gift_uniq'
            )
        ]


class Team(models.Model):
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='rating_teams')
    name = models.CharField(max_length=250)
    normalized_name = models.CharField(max_length=250, db_index=True)
    captain_name = models.CharField(max_length=250, blank=True)
    phone = models.CharField(max_length=16, blank=True)
    sms_allowed = models.BooleanField(default=False)
    consent_source = models.CharField(max_length=250, blank=True)
    consent_recorded_at = models.DateTimeField(blank=True, null=True)
    consent_recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='rating_consents_recorded',
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    archived_at = models.DateTimeField(blank=True, null=True)
    private_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('normalized_name', 'id')
        indexes = [
            models.Index(
                fields=('city', 'is_active', 'normalized_name'), name='rating_team_city_name_idx'
            )
        ]

    def __str__(self):
        return self.name


class TeamScore(models.Model):
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='scores')
    rating_format = models.ForeignKey(
        RatingFormat, on_delete=models.PROTECT, related_name='team_scores'
    )
    points = models.DecimalField(max_digits=18, decimal_places=1, default=0)
    games = models.PositiveIntegerField(default=0)
    current_rank = models.ForeignKey(
        Rank,
        on_delete=models.PROTECT,
        related_name='current_team_scores',
        blank=True,
        null=True,
    )
    version = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('team', 'rating_format'), name='rating_score_team_format_uniq'
            ),
            models.CheckConstraint(check=models.Q(points__gte=0), name='rating_score_points_nonnegative'),
            models.CheckConstraint(check=models.Q(games__gte=0), name='rating_score_games_nonnegative'),
        ]
        indexes = [
            models.Index(
                fields=('rating_format', 'current_rank', 'points'), name='rating_score_public_idx'
            ),
            models.Index(fields=('team', 'rating_format'), name='rating_score_team_format_idx'),
        ]


class ScoreAdjustment(models.Model):
    class Source(models.TextChoices):
        GAME_RESULT = 'game_result', 'Результат игры'
        CORRECTION = 'correction', 'Исправление'
        REVERSAL = 'reversal', 'Обратная операция'

    operation_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    payload_hash = models.CharField(max_length=64)
    team_score = models.ForeignKey(TeamScore, on_delete=models.PROTECT, related_name='adjustments')
    delta_points = models.DecimalField(max_digits=18, decimal_places=1, default=0)
    delta_games = models.IntegerField(default=0)
    reason = models.CharField(max_length=500)
    source = models.CharField(max_length=32, choices=Source.choices)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='rating_adjustments'
    )
    points_before = models.DecimalField(max_digits=18, decimal_places=1)
    points_after = models.DecimalField(max_digits=18, decimal_places=1)
    games_before = models.PositiveIntegerField()
    games_after = models.PositiveIntegerField()
    rank_before_level = models.PositiveSmallIntegerField(blank=True, null=True)
    rank_before_name = models.CharField(max_length=150, blank=True)
    rank_after_level = models.PositiveSmallIntegerField(blank=True, null=True)
    rank_after_name = models.CharField(max_length=150, blank=True)
    reverses = models.OneToOneField(
        'self',
        on_delete=models.PROTECT,
        related_name='reversal',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')
        constraints = [
            models.CheckConstraint(
                check=~(models.Q(delta_points=0) & models.Q(delta_games=0)),
                name='rating_adjustment_nonzero',
            )
        ]
        indexes = [
            models.Index(fields=('team_score', 'created_at'), name='rating_adj_score_time_idx')
        ]


class RankChangeEvent(models.Model):
    class Direction(models.TextChoices):
        INCREASE = 'increase', 'Повышение'
        DECREASE = 'decrease', 'Понижение'

    class Source(models.TextChoices):
        ADJUSTMENT = 'adjustment', 'Корректировка'
        CATALOG = 'catalog', 'Пересчёт каталога'
        MAINTENANCE = 'maintenance', 'Служебный пересчёт'

    team_score = models.ForeignKey(TeamScore, on_delete=models.PROTECT, related_name='rank_events')
    source_adjustment = models.OneToOneField(
        ScoreAdjustment,
        on_delete=models.PROTECT,
        related_name='rank_event',
        blank=True,
        null=True,
    )
    catalog_operation_id = models.UUIDField(blank=True, null=True)
    source = models.CharField(max_length=32, choices=Source.choices)
    direction = models.CharField(max_length=16, choices=Direction.choices)
    old_rank = models.ForeignKey(
        Rank, on_delete=models.PROTECT, related_name='+', blank=True, null=True
    )
    new_rank = models.ForeignKey(
        Rank, on_delete=models.PROTECT, related_name='+', blank=True, null=True
    )
    old_rank_level = models.PositiveSmallIntegerField(blank=True, null=True)
    old_rank_name = models.CharField(max_length=150, blank=True)
    new_rank_level = models.PositiveSmallIntegerField(blank=True, null=True)
    new_rank_name = models.CharField(max_length=150, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='acknowledged_rating_events',
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ('-detected_at', '-id')
        constraints = [
            models.UniqueConstraint(
                fields=('catalog_operation_id', 'team_score'),
                name='rating_event_catalog_score_uniq',
            )
        ]
        indexes = [
            models.Index(
                fields=('team_score', 'direction', 'acknowledged_at'),
                name='rating_event_score_ack_idx',
            )
        ]


class TeamRankAchievement(models.Model):
    class GiftStatus(models.TextChoices):
        PENDING = 'pending', 'Ожидает выдачи'
        ISSUED = 'issued', 'Выдано'
        CANCELLED = 'cancelled', 'Отменено'

    team_score = models.ForeignKey(TeamScore, on_delete=models.PROTECT, related_name='achievements')
    rank = models.ForeignKey(Rank, on_delete=models.PROTECT, related_name='achievements')
    source_event = models.ForeignKey(
        RankChangeEvent, on_delete=models.PROTECT, related_name='achievements'
    )
    first_achieved_at = models.DateTimeField(auto_now_add=True)
    rank_name_snapshot = models.CharField(max_length=150)
    gift_snapshot = models.TextField(blank=True)
    gift_status = models.CharField(
        max_length=16, choices=GiftStatus.choices, blank=True
    )
    gift_updated_at = models.DateTimeField(blank=True, null=True)
    gift_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='updated_rating_gifts',
        blank=True,
        null=True,
    )
    gift_comment = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('team_score', 'rank'), name='rating_achievement_score_rank_uniq'
            )
        ]


class GiftStatusChange(models.Model):
    operation_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    achievement = models.ForeignKey(
        TeamRankAchievement, on_delete=models.PROTECT, related_name='gift_changes'
    )
    old_status = models.CharField(max_length=16, blank=True)
    new_status = models.CharField(max_length=16, choices=TeamRankAchievement.GiftStatus.choices)
    comment = models.CharField(max_length=500, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='rating_gift_changes'
    )
    created_at = models.DateTimeField(auto_now_add=True)


class MessageDelivery(models.Model):
    class Status(models.TextChoices):
        QUEUED = 'queued', 'Ожидает отправки'
        PROCESSING = 'processing', 'Обрабатывается'
        ACCEPTED = 'accepted', 'Принято провайдером'
        DELIVERED = 'delivered', 'Доставлено'
        FAILED = 'failed', 'Ошибка'
        UNKNOWN = 'unknown', 'Результат неизвестен'
        SKIPPED = 'skipped', 'Пропущено'
        EXPIRED = 'expired', 'Истёк срок'

    event = models.ForeignKey(RankChangeEvent, on_delete=models.PROTECT, related_name='deliveries')
    channel = models.CharField(max_length=16, default='sms')
    provider = models.CharField(max_length=32, default='smspilot')
    recipient = models.CharField(max_length=16, blank=True)
    rendered_body = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    safe_error_code = models.CharField(max_length=64, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    provider_message_id = models.CharField(max_length=128, blank=True)
    provider_status_code = models.CharField(max_length=32, blank=True)
    parts = models.PositiveSmallIntegerField(blank=True, null=True)
    cost = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    next_attempt_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField()
    lease_token = models.UUIDField(blank=True, null=True)
    lease_until = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('event', 'channel'), name='rating_delivery_event_channel_uniq'
            )
        ]
        indexes = [
            models.Index(fields=('status', 'expires_at', 'created_at'), name='rating_delivery_queue_idx')
        ]


class MessageAttempt(models.Model):
    class Kind(models.TextChoices):
        AUTO = 'auto', 'Автоматическая отправка'
        MANUAL = 'manual', 'Ручной повтор'
        POLL = 'poll', 'Проверка статуса'

    operation_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    delivery = models.ForeignKey(MessageDelivery, on_delete=models.PROTECT, related_name='attempts')
    kind = models.CharField(max_length=16, choices=Kind.choices)
    result_status = models.CharField(max_length=16, choices=MessageDelivery.Status.choices)
    safe_error_code = models.CharField(max_length=64, blank=True)
    reason = models.CharField(max_length=500, blank=True)
    provider_status_code = models.CharField(max_length=32, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='rating_message_attempts',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)


class RatingPageSettings(models.Model):
    intro_title = models.CharField(max_length=250, default='Рейтинг команд')
    intro_text = models.TextField(blank=True)
    gifts_title = models.CharField(max_length=250, default='Поговорим о подарках?')
    gifts_text = models.TextField(blank=True)
    seo_title = models.CharField(max_length=250, blank=True)
    seo_description = models.TextField(blank=True)
    sms_template = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SmsIntegrationSettings(models.Model):
    sending_enabled = models.BooleanField(default=False)
    emergency_stop = models.BooleanField(default=True)
    sender_name = models.CharField(max_length=64, blank=True)
    test_mode = models.BooleanField(default=True)
    test_phone = models.CharField(max_length=16, blank=True)
    api_key_ciphertext = models.TextField(blank=True, editable=False)
    api_key_updated_at = models.DateTimeField(blank=True, null=True)
    api_key_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='updated_rating_sms_keys',
        blank=True,
        null=True,
        editable=False,
    )
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
