from django.urls import path

from . import views_public


urlpatterns = [
    path('', views_public.rating_public, name='public'),
]
