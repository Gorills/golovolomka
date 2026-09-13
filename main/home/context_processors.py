from .models import Page, City
from home.forms import GameOrderForm
from .city import get_subdomain, is_local_city_dev

def pages(request):
    return {'pages': Page.objects.exclude(type='partnery').order_by('page_order')}



def game_order_form(request):
    return {'game_order_form': GameOrderForm()}



def all_cities(request):
    return {'citys': City.objects.all()}




def contacts(request):
    return {
        'city': get_subdomain(request),
        'city_dev_local': is_local_city_dev(request),
    }
