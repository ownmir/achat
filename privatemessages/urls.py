from django.urls import path
from privatemessages import views


urlpatterns = [
    path('send_message/', views.send_message_view, name='send_message_view'),
    path('send_message_api/<int:thread_id>/', views.send_message_api_view, name='send_message_api_view'),
    path('chat/<int:thread_id>', views.chat_view, name='chat_view'),
    path('', views.messages_view, name='messages_view')
]
