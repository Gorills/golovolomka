import os
import uuid

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from PIL import Image, UnidentifiedImageError


ALLOWED_LOGO_FORMATS = frozenset({'PNG', 'JPEG', 'WEBP'})
ALLOWED_LOGO_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}
MAX_LOGO_BYTES = 2 * 1024 * 1024
MAX_LOGO_DIMENSION = 2048


def rank_logo_path(instance, filename):
    extension = os.path.splitext(filename or '')[1].lower()
    if extension not in ALLOWED_LOGO_EXTENSIONS:
        extension = '.img'
    return 'rating/ranks/{}{}'.format(uuid.uuid4().hex, extension)


@deconstructible
class RankLogoValidator:
    def __call__(self, uploaded):
        if uploaded.size > MAX_LOGO_BYTES:
            raise ValidationError('Логотип должен быть не больше 2 МБ')
        position = uploaded.tell() if hasattr(uploaded, 'tell') else None
        try:
            image = Image.open(uploaded)
            image.verify()
            image_format = image.format
            if image_format not in ALLOWED_LOGO_FORMATS:
                raise ValidationError('Допустимы только PNG, JPEG и WEBP')
            if position is not None:
                uploaded.seek(position)
            image = Image.open(uploaded)
            width, height = image.size
            if width > MAX_LOGO_DIMENSION or height > MAX_LOGO_DIMENSION:
                raise ValidationError('Размер логотипа не должен превышать 2048×2048 px')
        except (UnidentifiedImageError, OSError, ValueError):
            raise ValidationError('Файл не является допустимым изображением')
        finally:
            if position is not None:
                uploaded.seek(position)


validate_rank_logo = RankLogoValidator()
