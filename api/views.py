# views.py
from rest_framework import generics, permissions, views
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from rest_framework import status
from .serializers import UserSerializer, MessageSerializer, ChatRoomSerializer
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q, Max
from django.contrib.auth import get_user_model
from rest_framework.generics import RetrieveAPIView
from .models import ChatRoom, Message
UserModel = get_user_model()

class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        # Extract user data from request
        user_data = self.request.data
        username = user_data.get('username')
        
      
        # Check if the username, email, or mobile number already exists
        if User.objects.filter(username=username).exists():
            raise ValidationError({'username': 'A user with this Mobile Number already exists.'})
        
        # Save the user and profile
        serializer.save()


class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_chat_room_and_send_message(request, receiver_id):
    sender = request.user
    content = request.data.get('content')

    # Check if content is provided
    if not content:
        return Response({'error': 'Message content is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        receiver = User.objects.get(id=receiver_id)
    except User.DoesNotExist:
        return Response({'error': 'Receiver does not exist.'}, status=status.HTTP_404_NOT_FOUND)

    existing_chat_rooms = ChatRoom.objects.filter(users=sender).filter(users=receiver)

    if existing_chat_rooms.exists():
        chat_room = existing_chat_rooms.first()
    else:
        chat_room = ChatRoom.objects.create()
        chat_room.users.add(sender, receiver)

    message_data = {
        'chat_room': chat_room.id,
        'sender': sender.id,
        'content': content
    }
    message_serializer = MessageSerializer(data=message_data)

    if message_serializer.is_valid():
        message_serializer.save()
        return Response({
            'chat_room': ChatRoomSerializer(chat_room).data,
            'message': message_serializer.data
        }, status=status.HTTP_201_CREATED)
    else:
        return Response(message_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_rooms_for_logged_in_user(request):

    user = request.user

    chat_rooms = ChatRoom.objects.filter(users=user)
    
    data = []
    for room in chat_rooms:
        other_users = room.users.exclude(id=user.id)
        latest_message = Message.objects.filter(chat_room=room).order_by('-timestamp').first()
        latest_message_content = latest_message.content if latest_message else "No messages yet"
        latest_message_timestamp = latest_message.timestamp if latest_message else None
        
        room_data = {
            'id': room.id,
            'other_users': [{'id': other_user.id, 'first_name': other_user.first_name, 'username': other_user.username} for other_user in other_users],
            'latest_message': latest_message_content,
            'timestamp': latest_message_timestamp
        }
        data.append(room_data)

    return Response(data, status=status.HTTP_200_OK)



class ChatRoomView(generics.ListAPIView):
    serializer_class = ChatRoomSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        other_user_id = self.kwargs['other_user_id']
        current_user_id = self.kwargs['current_user_id']

        other_user = get_object_or_404(User, id=other_user_id)
        current_user = get_object_or_404(User, id=current_user_id)

        chat_rooms = ChatRoom.objects.filter(users__in=[current_user, other_user]).distinct()

        chat_rooms = [chat_room for chat_room in chat_rooms if 
                      chat_room.users.filter(id=current_user_id).exists() and
                      chat_room.users.filter(id=other_user_id).exists()]
        
        return chat_rooms

    def list(self, request, *args, **kwargs):
        chat_rooms = self.get_queryset()
        chat_room_data = []
        for chat_room in chat_rooms:
            chat_room_serializer = ChatRoomSerializer(chat_room)
            chat_room_id = chat_room_serializer.data['id']
            print(f"Chat Room ID: {chat_room_id}")
            
            # Get messages for the chat room
            messages = Message.objects.filter(chat_room=chat_room_id).order_by('timestamp')
            print(f"Messages: {messages}")
            
            message_serializer = MessageSerializer(messages, many=True)
            
            chat_room_data.append({
                'chat_room_id': chat_room_id,
                'messages': message_serializer.data
            })

        return Response(chat_room_data, status=status.HTTP_200_OK)
    