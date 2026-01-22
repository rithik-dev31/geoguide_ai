from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/location-greeting/', views.get_user_location_greeting, name='location_greeting'),
    path('api/chat/', views.chat_with_ai, name='chat'),
    path('api/place-details/', views.get_place_details_with_navigation, name='place_details'),
    path('api/enhanced-search/', views.enhanced_search, name='enhanced_search'),
    path('api/test/', views.test_api_status, name='test_api'),
    path('api/clear-chat/', views.clear_conversation, name='clear_chat'),
]