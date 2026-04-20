

from django.urls import re_path, path
from . import views

app_name = "account"
urlpatterns = [
    path("login/", views.login, name="account_login"),
    path("signup/", views.signup, name="account_signup"),
    path('logout/', views.Logout.as_view(), name='account_logout'),

    re_path(r'^profile/$', views.profile, name='account_profile'),
    re_path(r'^profile/update/$', views.profile_update, name='profile_update'),
    re_path(r'^profile/orders/$', views.profile_orders, name='profile_orders'),
    re_path(r'^profile/wishlist/$', views.profile_wishlist, name='profile_wishlist'),
    re_path(r'^profile/history/$', views.profile_history, name='profile_history'),
   


]