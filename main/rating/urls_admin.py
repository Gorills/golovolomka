from django.urls import path

from . import views_admin


urlpatterns = [
    path('', views_admin.team_list, name='team_list'),
    path('city/select/', views_admin.city_select, name='city_select'),
    path('teams/new/', views_admin.team_create, name='team_create'),
    path('teams/<int:team_id>/', views_admin.team_detail, name='team_detail'),
    path('teams/<int:team_id>/edit/', views_admin.team_edit, name='team_edit'),
    path('teams/<int:team_id>/archive/', views_admin.team_archive, name='team_archive'),
    path(
        'teams/<int:team_id>/formats/<slug:format_code>/adjust/',
        views_admin.score_adjust,
        name='score_adjust',
    ),
    path(
        'teams/<int:team_id>/formats/<slug:format_code>/adjust/commit/',
        views_admin.score_adjust_commit,
        name='score_adjust_commit',
    ),
    path(
        'teams/<int:team_id>/formats/<slug:format_code>/games/adjust/',
        views_admin.games_adjust,
        name='games_adjust',
    ),
    path(
        'adjustments/<int:adjustment_id>/reverse/',
        views_admin.adjustment_reverse,
        name='adjustment_reverse',
    ),
    path('events/', views_admin.event_list, name='event_list'),
    path('events/history/', views_admin.event_history, name='event_history'),
    path(
        'events/<int:event_id>/acknowledge/',
        views_admin.event_acknowledge,
        name='event_acknowledge',
    ),
    path(
        'achievements/<int:achievement_id>/gift-status/',
        views_admin.gift_status,
        name='gift_status',
    ),
    path('messages/', views_admin.message_incidents, name='message_incidents'),
    path(
        'messages/<int:delivery_id>/retry/',
        views_admin.message_retry,
        name='message_retry',
    ),
    path('messages/bulk/preview/', views_admin.bulk_message_preview, name='bulk_message_preview'),
    path('messages/bulk/commit/', views_admin.bulk_message_commit, name='bulk_message_commit'),
    path('catalog/', views_admin.catalog, name='catalog'),
    path(
        'catalog/ranks/<int:rank_id>/gift/',
        views_admin.city_rank_gift_update,
        name='city_rank_gift_update',
    ),
    path('catalog/formats/<int:format_id>/edit/', views_admin.format_edit, name='format_edit'),
    path('catalog/ranks/new/', views_admin.rank_create, name='rank_create'),
    path('catalog/ranks/<int:rank_id>/edit/', views_admin.rank_edit, name='rank_edit'),
    path(
        'catalog/ranks/<int:rank_id>/commit/',
        views_admin.rank_change_commit,
        name='rank_change_commit',
    ),
    path('integration/', views_admin.integration_settings, name='integration_settings'),
    path(
        'integration/test-send/',
        views_admin.integration_test_send,
        name='integration_test_send',
    ),
]
