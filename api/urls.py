from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


urlpatterns = [
    path('register/', views.CreateUserView.as_view(), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='get_token'),
    path('token/refresh', TokenRefreshView.as_view(), name='refresh_token'),

    path('user/', views.UserDetailView.as_view(), name='user_detail'),
    
    path('create-chat/<int:receiver_id>/', views.create_chat_room_and_send_message, name='create-chat'),
    path('my-chat-rooms/', views.get_chat_rooms_for_logged_in_user, name='my-chat-rooms'),
    path('chat_rooms/<int:other_user_id>/<int:current_user_id>/', views.ChatRoomView.as_view(), name='chat-room-list'),
   
]