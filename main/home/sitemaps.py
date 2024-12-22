from django.contrib.sitemaps import Sitemap
from django.shortcuts import reverse



from .models import Page

from django.utils import timezone


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
    



