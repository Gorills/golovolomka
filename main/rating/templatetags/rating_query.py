from django import template


register = template.Library()
ALLOWED = ('format', 'q', 'sort', 'direction', 'page')


@register.simple_tag(takes_context=True)
def rating_querystring(context, **updates):
    request = context['request']
    query = request.GET.copy()
    for key in list(query.keys()):
        if key not in ALLOWED:
            query.pop(key, None)
    for key, value in updates.items():
        if key not in ALLOWED:
            continue
        if value in (None, ''):
            query.pop(key, None)
        else:
            query[key] = value
    encoded = query.urlencode()
    return '?{}'.format(encoded) if encoded else ''
