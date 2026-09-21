from django.contrib.sitemaps import Sitemap
from django.shortcuts import reverse



from .models import Page

from django.utils import timezone
from django.conf import settings
from .models import City


class StaticViewSitemap(Sitemap):
    def items(self):
        return [
            'home',
            
     
            ]
    def location(self, item):
        return reverse(item)
    
    def lastmod(self, item):
        # Замените эту строку на логику получения даты модификации для каждой страницы
        # Ниже пример с использованием текущей даты и времени
        if item == 'home':
            # Ваша логика для страницы 'home'
            return timezone.now()
       
        
    def priority(self, item):
        if item == 'home':
            # Приоритет для страницы 'home'
            return 1.0
        
        else:
            # Вернуть None или другое значение при отсутствии информации о приоритете
            return None

    
class PageSitemap(Sitemap):
    def items(self):
        return Page.objects.all()

    def lastmod(self, item):
        return item.updated_at
    
    def priority(self, item):
        return 0.8


class CityRatingSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return City.objects.all().order_by('slug')

    def get_urls(self, page=1, site=None, protocol=None):
        template = getattr(
            settings,
            'RATING_PUBLIC_URL_TEMPLATE',
            'https://{city}.golovolomka.fun/rating/',
        )
        return [
            {
                'item': city,
                'location': template.format(city=city.slug),
                'lastmod': None,
                'changefreq': self.changefreq,
                'priority': self.priority,
            }
            for city in self.items()
        ]

