from django.urls import path, include
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from rest_framework.routers import DefaultRouter

# Create a router instance
api_router = DefaultRouter()
api_router.register(r'chatbot', views.ChatbotViewSet, basename='chatbot')

urlpatterns = [
    path('register/', views.CreateUserView.as_view(), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='get_token'),
    path('token/refresh', TokenRefreshView.as_view(), name='refresh_token'),

    path('user/', views.UserDetailView.as_view(), name='user_detail'),
    
    path('message/<int:sender_id>/<int:receiver_id>/', views.MessageUserView.as_view(), name='message-user'),
    #path('chat-room/<int:sender_id>/<int:receiver_id>/', views.ChatRoomMessagesView.as_view(), name='message-user'),
    path('chat-room/<int:current_user_id>/<int:user_id>/', views.get_chat_room_messages, name='chat-room-messages'),
    path('superusers/', views.SuperuserListView.as_view(), name='superuser-list'),
    path('users/', views.UserListView.as_view(), name='superuser-list'),
    path('chat/rooms/', views.UserChatRoomsView.as_view(), name='user-chat-rooms'),
    path('user/<int:id>/', views.UserInfoView.as_view(), name='user-detail'),
    # Include the chatbot router
    path('', include(api_router.urls)),
]