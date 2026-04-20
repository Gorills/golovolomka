from .models import Page, City
from setup.models import BaseSettings
from home.forms import GameOrderForm
from django.http import HttpRequest

def pages(request):
    return {'pages': Page.objects.exclude(type='partnery').order_by('page_order')}



def game_order_form(request):
    return {'game_order_form': GameOrderForm()}



def get_subdomain(request: HttpRequest):
    # Получаем хост из запроса (например, "localhost:8000")
    host = request.get_host()
    
    # Разбиваем хост на части
    parts = host.split('.')
    
    # Убираем порт, если он есть (например, "localhost:8000" -> "localhost")
    if ':' in parts[-1]:
        parts[-1] = parts[-1].split(':')[0]
    
    # Проверяем, есть ли субдомен
    if len(parts) > 2:  # Например, ['krasnodar', 'localhost']
        subdomain = parts[0]  # Берем первую часть как субдомен
    else:
        subdomain = None  # Нет субдомена
    
    # Ищем город по slug, если субдомен найден
    if subdomain:
        return City.objects.filter(slug=subdomain).first()
    return None



def all_cities(request):
    return {'citys': City.objects.all()}




def contacts(request):

    city = get_subdomain(request)


    return {'city': city}
