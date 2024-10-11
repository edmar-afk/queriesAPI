# views.py
from rest_framework import generics, permissions, views
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from rest_framework import status, viewsets
from .serializers import UserSerializer, MessageSerializer, ChatRoomSerializer,ChatbotSerializer
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q, Max
from django.contrib.auth import get_user_model
from rest_framework.generics import RetrieveAPIView, ListAPIView
from .models import ChatRoom, Message
UserModel = get_user_model()
import json
from difflib import get_close_matches
from django.conf import settings
import os
BASE_DIR = settings.BASE_DIR
from sentence_transformers import SentenceTransformer, util

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

class SuperuserListView(ListAPIView):
    queryset = User.objects.filter(is_superuser=True).exclude(username='admin')  # Exclude 'admin' user
    serializer_class = UserSerializer
    
class UserListView(ListAPIView):
    queryset = User.objects.filter(is_superuser=False).exclude(username='admin')  # Exclude 'admin' user
    serializer_class = UserSerializer    






class MessageUserView(APIView):
    def post(self, request, sender_id, receiver_id):
        # Get the sender and receiver users
        sender = get_object_or_404(User, id=sender_id)
        receiver = get_object_or_404(User, id=receiver_id)

        # Check if a chat room exists with these two users
        chat_room = ChatRoom.objects.filter(users=sender).filter(users=receiver).first()

        # If no chat room exists, create a new one
        if not chat_room:
            chat_room = ChatRoom.objects.create()
            chat_room.users.add(sender, receiver)
            chat_room.save()

        # Create a new message in the chat room
        message_data = {
            'sender': sender.id,
            'chat_room': chat_room.id,
            'content': request.data.get('content')
        }
        message_serializer = MessageSerializer(data=message_data)

        if message_serializer.is_valid():
            message_serializer.save()
            return Response(message_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(message_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        





class ChatRoomMessagesView(APIView):
    def get(self, request, current_user_id, user_id):
        try:
            # Fetch the two users
            current_user = User.objects.get(id=current_user_id)
            other_user = User.objects.get(id=user_id)

            # Check if a room exists with both users, regardless of order
            chat_room = ChatRoom.objects.filter(users=current_user).filter(users=other_user).distinct().first()

            if not chat_room:
                # If no room exists, create one
                chat_room = ChatRoom.objects.create()
                chat_room.users.set([current_user, other_user])
                chat_room.save()

            # Retrieve all messages in this room
            messages = Message.objects.filter(chat_room=chat_room).order_by('timestamp')

            # Serialize the data
            room_serializer = ChatRoomSerializer(chat_room)
            messages_serializer = MessageSerializer(messages, many=True)

            # Return chat room and message data
            return Response({
                'chat_room': room_serializer.data,
                'messages': messages_serializer.data
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        



@api_view(['GET'])
def get_chat_room_messages(request, current_user_id, user_id):
    try:
        # Check if a chat room exists between the two users
        chat_room = ChatRoom.objects.filter(users__id=current_user_id).filter(users__id=user_id).distinct().first()

        # If no chat room exists, return empty messages list (or create a room if required)
        if not chat_room:
            return Response({'messages': []})

        # Get messages from the chat room
        messages = Message.objects.filter(chat_room=chat_room).order_by('timestamp')

        # Serialize the message data
        serializer = MessageSerializer(messages, many=True)
        return Response({'messages': serializer.data})
    
    except User.DoesNotExist:
        return Response({'error': 'User does not exist'}, status=404)
    
    


class UserChatRoomsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Filter chat rooms where the current user is a member
        user = request.user
        chat_rooms = ChatRoom.objects.filter(users=user)

        # Serialize the chat rooms with the other user info
        serializer = ChatRoomSerializer(chat_rooms, many=True, context={'request': request})
        return Response(serializer.data)
    
    
    

class UserInfoView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'id'












# Load the knowledge base from a JSON file
def load_knowledge_base(file_path: str):
    full_path = os.path.join(BASE_DIR, file_path)
    with open(full_path, 'r') as file:
        data = json.load(file)
    return data

# Save the updated knowledge base to the JSON file
def save_knowledge_base(file_path: str, data: dict):
    full_path = os.path.join(BASE_DIR, file_path)
    with open(full_path, 'w') as file:
        json.dump(data, file, indent=2)


def find_best_match(user_question: str, questions: list[str]) -> str | None:
    matches = get_close_matches(user_question, questions, n=1, cutoff=0.6)
    return matches[0] if matches else None

def get_answer_for_question(question: str, knowledge_base: dict) -> str | None:
    for q in knowledge_base["questions"]:
        if q["question"] == question:
            return q["answer"]
    return None

class ChatbotViewSet(viewsets.ViewSet):
    serializer_class = ChatbotSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user_question = serializer.validated_data['question']
            knowledge_base = load_knowledge_base('knowledge_base.json')
            best_match = find_best_match(user_question, [q["question"] for q in knowledge_base["questions"]])

            if best_match:
                answer = get_answer_for_question(best_match, knowledge_base)
                return Response({'answer': answer}, status=status.HTTP_200_OK)
            else:
                return Response({'answer': "I'm not entirely sure about that, so it might be best to check with the person in charge to get a more accurate answer. They should be able to provide the correct information."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)