import uuid

from django import forms
from django.db.models import Q
from django.db.models.functions import Length

from .models import (
    Rank,
    RatingFormat,
    RatingPageSettings,
    ScoreAdjustment,
    SmsIntegrationSettings,
    TeamRankAchievement,
)
from .services import ValidationError as DomainValidationError
from .services import canonical_phone, normalize_team_name, parse_points, validate_sms_template


def _bounded_edit_distance(left, right, limit=2):
    if abs(len(left) - len(right)) > limit:
        return limit + 1
    previous = list(range(len(right) + 1))
    for row_index, left_char in enumerate(left, start=1):
        current = [row_index]
        row_minimum = row_index
        for column_index, right_char in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column_index] + 1,
                    previous[column_index - 1] + (left_char != right_char),
                )
            )
            row_minimum = min(row_minimum, current[-1])
        if row_minimum > limit:
            return limit + 1
        previous = current
    return previous[-1]


def _has_similar_team(queryset, normalized_name):
    if queryset.filter(normalized_name=normalized_name).exists():
        return True
    length = len(normalized_name)
    prefix = normalized_name[:4]
    last_token = normalized_name.rsplit(' ', 1)[-1][:4]
    anchors = Q(normalized_name__startswith=prefix)
    if last_token:
        anchors |= Q(normalized_name__icontains=last_token)
    candidates = (
        queryset.annotate(name_length=Length('normalized_name'))
        .filter(
            anchors,
            name_length__gte=max(1, length - 2),
            name_length__lte=length + 2,
        )
        .order_by('id')
        .values_list('normalized_name', flat=True)[:50]
    )
    return any(
        _bounded_edit_distance(normalized_name, candidate, limit=2) <= 2
        and abs(len(normalized_name) - len(candidate)) <= max(1, int(length * 0.15))
        for candidate in candidates
    )


class CitySelectForm(forms.Form):
    city = forms.ChoiceField(choices=())
    next = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, cities=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['city'].choices = [(city.slug, city.name) for city in cities]


class TeamForm(forms.Form):
    name = forms.CharField(max_length=250, label='Название команды')
    captain_name = forms.CharField(max_length=250, required=False, label='Капитан')
    phone = forms.CharField(max_length=32, required=False, label='Телефон')
    sms_allowed = forms.BooleanField(required=False, label='Разрешены сообщения о ранге')
    consent_source = forms.CharField(max_length=250, required=False, label='Источник согласия')
    consent_recorded_at = forms.DateTimeField(
        required=False,
        label='Дата согласия',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
    )
    private_note = forms.CharField(required=False, label='Служебный комментарий', widget=forms.Textarea)
    confirm_duplicate = forms.BooleanField(
        required=False, label='Я проверил возможное совпадение и подтверждаю сохранение'
    )

    def __init__(self, *args, city=None, team=None, **kwargs):
        self.city = city
        self.team = team
        super().__init__(*args, **kwargs)

    def clean_name(self):
        value = self.cleaned_data['name']
        if not normalize_team_name(value):
            raise forms.ValidationError('Введите название команды')
        return ' '.join(value.split())

    def clean_phone(self):
        try:
            return canonical_phone(self.cleaned_data.get('phone'))
        except DomainValidationError as exc:
            raise forms.ValidationError(str(exc))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('sms_allowed') and not (
            cleaned.get('phone')
            and cleaned.get('consent_source')
            and cleaned.get('consent_recorded_at')
        ):
            raise forms.ValidationError(
                'Для SMS укажите телефон, источник и дату подтверждения согласия'
            )
        if self.city and cleaned.get('name') and not cleaned.get('confirm_duplicate'):
            from .models import Team

            possible = Team.objects.filter(city=self.city)
            if self.team:
                possible = possible.exclude(pk=self.team.pk)
            phone = cleaned.get('phone')
            same_phone = bool(phone and possible.filter(phone=phone).exists())
            similar_name = _has_similar_team(
                possible, normalize_team_name(cleaned['name'])
            )
            if same_phone or similar_name:
                raise forms.ValidationError(
                    'В этом городе уже есть похожая команда. Проверьте совпадение и подтвердите.'
                )
        return cleaned


class OperationForm(forms.Form):
    operation_id = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.initial.get('operation_id'):
            self.initial['operation_id'] = uuid.uuid4()


class ScoreAdjustmentForm(OperationForm):
    delta_points = forms.CharField(initial='0', label='Изменение баллов')
    delta_games = forms.IntegerField(initial=0, label='Изменение количества игр')
    reason = forms.CharField(max_length=500, label='Основание')
    source = forms.ChoiceField(
        choices=(
            (ScoreAdjustment.Source.GAME_RESULT, 'Результат игры'),
            (ScoreAdjustment.Source.CORRECTION, 'Исправление'),
        ),
        label='Тип операции',
    )
    expected_version = forms.IntegerField(widget=forms.HiddenInput)

    def clean_delta_points(self):
        try:
            return parse_points(self.cleaned_data['delta_points'])
        except DomainValidationError as exc:
            raise forms.ValidationError(str(exc))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('delta_points') == 0 and cleaned.get('delta_games') == 0:
            raise forms.ValidationError('Укажите изменение баллов или игр')
        return cleaned


class AdjustmentCommitForm(forms.Form):
    preview_token = forms.CharField(widget=forms.HiddenInput)


class ReversalForm(OperationForm):
    reason = forms.CharField(max_length=500, label='Причина обратной операции')


class GamesAdjustmentForm(OperationForm):
    delta_games = forms.IntegerField(min_value=-100000, max_value=100000)
    reason = forms.CharField(max_length=500)
    expected_version = forms.IntegerField(widget=forms.HiddenInput)

    def clean_delta_games(self):
        value = self.cleaned_data['delta_games']
        if value == 0:
            raise forms.ValidationError('Изменение не может быть нулевым')
        return value


class AcknowledgeEventForm(OperationForm):
    pass


class GiftStatusForm(OperationForm):
    status = forms.ChoiceField(choices=TeamRankAchievement.GiftStatus.choices)
    comment = forms.CharField(max_length=500, required=False)


class CityRankGiftForm(forms.Form):
    gift = forms.CharField(
        max_length=2000,
        required=False,
        label='Подарок в этом городе',
        widget=forms.Textarea(attrs={'rows': 3}),
    )


class MessageRetryForm(OperationForm):
    reason = forms.CharField(max_length=500)
    confirm_unknown = forms.BooleanField(required=False)


class RankForm(forms.ModelForm):
    class Meta:
        model = Rank
        fields = (
            'rating_format', 'level', 'min_points', 'name', 'logo', 'logo_alt',
            'description', 'gift', 'is_active',
        )

    def __init__(self, *args, **kwargs):
        self.lock_format = kwargs.pop('lock_format', False)
        super().__init__(*args, **kwargs)
        if self.lock_format:
            self.fields['rating_format'].disabled = True
            self.fields['level'].disabled = True


class RatingFormatForm(forms.ModelForm):
    class Meta:
        model = RatingFormat
        fields = ('name', 'description', 'order', 'is_active')


class RatingPageSettingsForm(forms.ModelForm):
    class Meta:
        model = RatingPageSettings
        fields = (
            'intro_title', 'intro_text', 'gifts_title', 'gifts_text', 'seo_title',
            'seo_description', 'sms_template',
        )

    def clean_sms_template(self):
        value = self.cleaned_data['sms_template']
        try:
            validate_sms_template(value)
        except DomainValidationError as exc:
            raise forms.ValidationError(str(exc))
        return value


class SmsIntegrationSettingsForm(forms.ModelForm):
    api_key = forms.CharField(
        required=False,
        label='Новый API-ключ',
        widget=forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'}),
    )
    clear_api_key = forms.BooleanField(required=False, label='Удалить сохранённый ключ')

    class Meta:
        model = SmsIntegrationSettings
        fields = ('sending_enabled', 'emergency_stop', 'sender_name', 'test_mode', 'test_phone')

    def clean_test_phone(self):
        try:
            return canonical_phone(self.cleaned_data.get('test_phone'))
        except DomainValidationError as exc:
            raise forms.ValidationError(str(exc))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('api_key') and cleaned.get('clear_api_key'):
            raise forms.ValidationError('Выберите замену или удаление ключа')
        return cleaned


class BulkMessageForm(OperationForm):
    operation_id = forms.UUIDField(required=False, widget=forms.HiddenInput)
    statuses = forms.MultipleChoiceField(
        choices=(('failed', 'Ошибка'), ('unknown', 'Неизвестно')),
        initial=('failed',),
    )
    confirm_unknown = forms.BooleanField(required=False)
    reason = forms.CharField(
        max_length=500,
        required=False,
        initial='Массовый ручной повтор',
        label='Основание массового повтора',
    )

    def clean(self):
        cleaned = super().clean()
        cleaned['operation_id'] = cleaned.get('operation_id') or uuid.uuid4()
        cleaned['reason'] = (cleaned.get('reason') or 'Массовый ручной повтор').strip()
        return cleaned


class BulkCommitForm(forms.Form):
    preview_token = forms.CharField(widget=forms.HiddenInput)
