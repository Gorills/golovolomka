from django import template
register = template.Library()
from setup.models import ThemeSettings
try:
    theme_address = ThemeSettings.objects.get().name
except:
    theme_address = 'default'

@register.simple_tag()
def get_static(file):
    return '/core/theme/'+theme_address+'/' + file


@register.simple_tag()
def get_libs(file):
    return '/core/libs/' + file



@register.simple_tag()
def get_video(file):
    return '/core/video/' + file