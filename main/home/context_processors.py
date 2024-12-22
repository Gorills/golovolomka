from .models import Page, City
from setup.models import BaseSettings
from home.forms import GameOrderForm


def pages(request):
    return {'pages': Page.objects.exclude(type='partnery').order_by('page_order')}



def game_order_form(request):
    return {'game_order_form': GameOrderForm()}


def get_subdomain(request):
    hostname = request.build_absolute_uri()
    subdomain_parts = hostname.split('.')
    
    # Проверяем количество частей субдомена.
    # Если их меньше или равно 3, то это не субдомен четвертого уровня
    if len(subdomain_parts) <= 3:
        subdomain = str(subdomain_parts[0]).replace('www.', '').replace('http://', '').replace('https://', '')
        return City.objects.filter(slug=subdomain).first()
    
    # Если количество частей субдомена больше 3, то игнорируем его
    return None


def contacts(request):

    city = get_subdomain(request)

    if city:
        contacts_get = {
            'city': city.name,
            'phone': city.phone,
            'address': city.address,
            'email': city.email,
            'vk': city.vk,
            'instagram': city.instagram,
            'telegram': city.telegram,
            'whatsapp': city.whatsapp
        }

    else:
        contacts_get = {
            'city': BaseSettings.objects.get().name,
            'phone': BaseSettings.objects.get().phone,
            'address': BaseSettings.objects.get().address,
            'email': BaseSettings.objects.get().email,
            'vk': BaseSettings.objects.get().vk,
            'instagram': BaseSettings.objects.get().instagram,
            'telegram': BaseSettings.objects.get().telegram,
            'whatsapp': BaseSettings.objects.get().whatsapp
        }


    return {'contacts': contacts_get}
