from django import template
register = template.Library()

@register.simple_tag()
def get_static(file):
    return '/core/admin/' + file


@register.simple_tag()
def get_libs(file):
    return '/core/libs/' + file