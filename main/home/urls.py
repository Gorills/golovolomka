
from django.urls import path

from django.contrib.sitemaps.views import sitemap
from .sitemaps import *
from . import views
from django.views.generic.base import RedirectView

sitemaps = {
    'static': StaticViewSitemap,
    'page': PageSitemap,
    

}


urlpatterns = [
    path('', views.home, name='home'),
    path('corp/', views.corp, name='corp'),
    path('franchise/', views.franchise, name='franchise'),

    path('game_callback/', views.game_callback, name='game_callback'),
    path('schedule/', views.schedule, name='schedule'),
    path("robots.txt", views.robots_txt),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.index'),

    path('<slug:slug>/', views.page_detail, name='page_detail'),



 




    
 
]

