from django.db import IntegrityError, transaction


FORMATS = (
    ('classic', 'Классика'),
    ('musicality', 'Музыкалити'),
    ('fans', 'Фанаты'),
)

RANK_NAMES = {
    'classic': (
        'Андромеда', 'Орион', 'Малая Медведица', 'Кассиопея', 'Цефей', 'Персей',
        'Альфа Центавра', 'Пегас', 'Большая Медведица', 'Астра', 'Альтаир', 'Сириус',
    ),
    'musicality': (
        'Иванушки', 'Корни', 'Звери', 'Нирвана', 'Расмусы', 'Рамштайны',
        'Аэросмит', 't.A.T.u', 'Скорпионсы', 'Битлы', 'Квин', 'Джексоны',
    ),
    'fans': (
        'Ай-Петри', 'Везувий', 'Батур', 'Рашмор', 'Синай', 'Фудзияма',
        'Арарат', 'Монблан', 'Эльбрус', 'Килиманджаро', 'Эверест', 'Олимп',
    ),
}

THRESHOLDS = (300, 700, 1500, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000)
GIFTS = {
    4: 'Именная табличка команды',
    5: 'Сувенирный мерч от «Головоломки»',
    6: 'Бесплатное посещение любой тематической игры всей командой',
    7: 'Набор подарков от партнёров «Головоломки»',
    8: 'Именной мерч от «Головоломки» для команды',
    9: 'Сертификат на игры номиналом 5 000 рублей',
    10: 'Набор подарков от партнёров «Головоломки»',
    11: 'Бесплатное посещение любой игры всей командой',
    12: 'Сертификат на игры номиналом 10 000 рублей, ящик шампанского и церемониальное награждение на игре',
}


def seed_catalog(RatingFormat, Rank, RatingPageSettings=None, SmsIntegrationSettings=None):
    result = {'created_formats': 0, 'created_ranks': 0, 'skipped_rank_conflicts': []}
    for order, (code, name) in enumerate(FORMATS, start=1):
        rating_format, format_created = RatingFormat.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'description': (
                    'Все тематические игры' if code == 'fans' else ''
                ),
                'order': order,
                'is_active': True,
            },
        )
        if format_created:
            result['created_formats'] += 1
        for level, (threshold, rank_name) in enumerate(
            zip(THRESHOLDS, RANK_NAMES[code]), start=1
        ):
            if Rank.objects.filter(rating_format=rating_format, level=level).exists():
                continue
            if Rank.objects.filter(
                rating_format=rating_format, min_points=threshold
            ).exists():
                result['skipped_rank_conflicts'].append(
                    {'format_code': code, 'level': level, 'min_points': threshold}
                )
                continue
            try:
                with transaction.atomic():
                    Rank.objects.create(
                        rating_format=rating_format,
                        level=level,
                        min_points=threshold,
                        name=rank_name,
                        gift=GIFTS.get(level, ''),
                        is_active=True,
                    )
            except IntegrityError:
                result['skipped_rank_conflicts'].append(
                    {'format_code': code, 'level': level, 'min_points': threshold}
                )
            else:
                result['created_ranks'] += 1
    if RatingPageSettings is not None:
        RatingPageSettings.objects.get_or_create(pk=1)
    if SmsIntegrationSettings is not None:
        SmsIntegrationSettings.objects.get_or_create(pk=1)
    return result
