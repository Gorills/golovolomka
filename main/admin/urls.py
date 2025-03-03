
from django.urls import path, re_path
from . import views


urlpatterns = [
    path('', views.admin, name='admin'),
    path('general_settings/', views.general_settings, name='general_settings'), 
    path('codes/', views.codes_settings, name='codes_settings'),
    path('codes/edit/<int:pk>/', views.codes_settings_edit, name='codes_settings_edit'),
    path('codes/delete/<int:pk>/', views.codes_settings_delete, name='codes_settings_delete'),

    path('color_settings/', views.color_settings, name='color_settings'),
    path('theme_settings/', views.theme_settings, name='theme_settings'),

    
    path('subdomains/', views.subdomains, name='subdomains'),
    path('subdomains/add/', views.subdomains_add, name='subdomains_add'),
    path('subdomains/delete/<int:pk>/', views.subdomains_delete, name='subdomains_delete'),
    path('subdomains/edit/<int:pk>/', views.subdomains_edit, name='subdomains_edit'),


    path('orders/', views.orders, name='orders'),
    path('order/add/', views.order_add, name='order_add'),
    path('order/edit/<int:pk>/', views.order_edit, name='order_edit'),
    path('order/delete/<int:pk>/', views.order_delete, name='order_delete'),


    path('games/', views.games, name='games'),
    path('geme_cat_add/', views.geme_cat_add, name='geme_cat_add'),
    path('geme_cat_edit/<int:pk>/', views.geme_cat_edit, name='geme_cat_edit'),
    path('game_cat_delete/<int:pk>/', views.game_cat_delete, name='game_cat_delete'),

    path('game_add/', views.game_add, name='game_add'),
    path('game_edit/<int:pk>/', views.game_edit, name='game_edit'),
    path('game_delete/<int:pk>/', views.game_delete, name='game_delete'),


    path('what/', views.what, name='what'),
    path('what/add/', views.what_add, name='what_add'),
    path('what/edit/<int:pk>/', views.what_edit, name='what_edit'),
    path('what/delete/<int:pk>/', views.what_delete, name='what_delete'),


    path('wait/', views.wait, name='wait'),
    path('wait/add/', views.wait_add, name='wait_add'),
    path('wait/edit/<int:pk>/', views.wait_edit, name='wait_edit'),
    path('wait/delete/<int:pk>/', views.wait_delete, name='wait_delete'),

    path('photos/add/', views.photo_add, name='photo_add'),
    path('photos/edit/<int:pk>/', views.photo_edit, name='photo_edit'),
    path('photos/delete/<int:pk>/', views.photo_delete, name='photo_delete'),



    path('faq/', views.faq, name='faq'),
    path('faq/add/', views.faq_add, name='faq_add'),
    path('faq/edit/<int:pk>/', views.faq_edit, name='faq_edit'),
    path('faq/delete/<int:pk>/', views.faq_delete, name='faq_delete'),


    path('btn_block/', views.btn_block, name='btn_block'),
    path('btn_block/add/', views.btn_block_add, name='btn_block_add'),
    path('btn_block/edit/<int:pk>/', views.btn_block_edit, name='btn_block_edit'),
    path('btn_block/delete/<int:pk>/', views.btn_block_delete, name='btn_block_delete'),

    path('home_games', views.home_games, name='home_games'),

    # SLIDER
    path('static/slider/', views.admin_slider, name='admin_slider'),
    path('static/slider/add/', views.slider_add, name='slider_add'),
    path('static/slider/edit/<int:pk>/', views.slider_edit, name='slider_edit'),
    path('static/slider/delete/<int:pk>/', views.slider_delete, name='slider_delete'),


    # PAGES
    path('static/pages/', views.admin_pages, name='admin_pages'),
    path('static/pages/add/', views.page_add, name='page_add'),
    path('static/pages/edit/<int:pk>/', views.page_edit, name='page_edit'),



    # USERS
    path('users/', views.admin_users, name='admin_users'),
    path('users/delete/<int:pk>/', views.users_delete, name='users_delete'),



    # CORP
    path('start/corp/', views.admin_corp, name='admin_corp'),
    path('whatcorpi/corp/', views.admin_what_corp, name='admin_what_corp'),
    path('whatcorpa/corp/items/', views.admin_what_corp_items, name='admin_what_corp_items'),
    path('whatcorpe/corp/items/add/', views.admin_what_corp_items_add, name='admin_what_corp_items_add'),
    path('whatcorp/corp/items/edit/<int:pk>/', views.admin_what_corp_items_edit, name='admin_what_corp_items_edit'),
    path('whatcorp/corp/items/delete/<int:pk>/', views.admin_what_corp_items_delete, name='admin_what_corp_items_delete'),

    path('why_we/corp/', views.admin_why_we_corp, name='admin_why_we_corp'),
    path('why_we/corp/add/', views.admin_why_we_corp_add, name='admin_why_we_corp_add'),
    path('why_we/corp/edit/<int:pk>/', views.admin_why_we_corp_edit, name='admin_why_we_corp_edit'),
    path('why_we/corp/delete/<int:pk>/', views.admin_why_we_corp_delete, name='admin_why_we_corp_delete'),

    path('dover/corp/', views.admin_dover_corp, name='admin_dover_corp'),
    path('dover/corp/add/', views.admin_dover_corp_add, name='admin_dover_corp_add'),
    path('dover/corp/edit/<int:pk>/', views.admin_dover_corp_edit, name='admin_dover_corp_edit'),
    path('dover/corp/delete/<int:pk>/', views.admin_dover_corp_delete, name='admin_dover_corp_delete'),

    path('franch/<str:model_name>/edit/<int:item_id>/', views.admin_franch_edit, name='admin_franch_edit'),
    path('franch/<str:model_name>/delete/<int:item_id>/', views.admin_franch_delete, name='admin_franch_delete'),
    # FRANCH
    # Без дополнительных моделей
    re_path(r'^franch/(?P<model_name>[^/]+)/$', views.admin_franch, name='admin_franch'),

    # С одной дополнительной моделью (items1_model_name)
    re_path(r'^franch/(?P<model_name>[^/]+)/(?P<items1_model_name>[^/]+)/$', views.admin_franch, name='admin_franch_with_items'),

    # С двумя дополнительными моделями (items1_model_name и items2_model_name)
    re_path(r'^franch/(?P<model_name>[^/]+)/(?P<items1_model_name>[^/]+)/(?P<items2_model_name>[^/]+)/$', views.admin_franch, name='admin_franch_with_two_items'),
    
    
     

]


