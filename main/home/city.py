"""Определение текущего города по хосту (прод) и локальный переключатель."""
from django.conf import settings
from django.http import HttpRequest

from .models import City

DEV_CITY_SESSION_KEY = 'dev_city'
DEV_CITY_RESET = '-'
LOCAL_HOSTS = frozenset({'localhost', '127.0.0.1'})


def hostname(request: HttpRequest) -> str:
    return request.get_host().split(':')[0]


def is_local_city_dev(request: HttpRequest) -> bool:
    host = hostname(request)
    return host in LOCAL_HOSTS or host.endswith('.localhost')


def _city_from_subdomain(request: HttpRequest):
    host = hostname(request)
    parts = host.split('.')

    if host.endswith('.localhost') and host != 'localhost':
        slug = parts[0]
    elif len(parts) > 2:
        slug = parts[0]
    else:
        return None

    return City.objects.filter(slug=slug).first()


def _city_from_dev_switch(request: HttpRequest):
    slug = request.GET.get('city')
    session = getattr(request, 'session', None)

    if slug is not None:
        if slug == '' or slug == DEV_CITY_RESET:
            if session is not None:
                session.pop(DEV_CITY_SESSION_KEY, None)
            return None
        city = City.objects.filter(slug=slug).first()
        if city and session is not None:
            session[DEV_CITY_SESSION_KEY] = city.slug
        return city

    if session is not None:
        stored = session.get(DEV_CITY_SESSION_KEY)
        if stored:
            city = City.objects.filter(slug=stored).first()
            if city:
                return city

    default_slug = getattr(settings, 'DEV_CITY', None)
    if default_slug:
        return City.objects.filter(slug=default_slug).first()
    return None


def get_subdomain(request: HttpRequest):
    city = _city_from_subdomain(request)
    if city:
        return city
    if is_local_city_dev(request):
        return _city_from_dev_switch(request)
    return None
