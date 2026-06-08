import json
import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

class TaskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.group_name = f'project_{self.project_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Optionally handle messages from client
        pass

   # handler for task status updates
    async def task_update(self, event):
        await self.send(text_data=json.dumps(event['data']))

    # handler for new task additions
    async def task_added(self, event):
        await self.send(text_data=json.dumps({
            'action': 'add',
            'task': event['data']
        }))

    #handler for task edits
    async def task_edited(self, event):
        await self.send(text_data=json.dumps({
            "action": "edit",
            "task": event["data"],
        }))
        
    # handler for task deletions
    async def task_deleted(self, event):
        await self.send(text_data=json.dumps({
            'action': 'delete',
            'task_id': event['data']['task_id']
        }))

    # New: soft-disable/restore
    async def task_disabled(self, event):
        # Expecting: data.task_id
        await self.send(text_data=json.dumps({
            "action": "disable",
            "task_id": event["data"]["task_id"],
        }))

    async def task_restored(self, event):
        await self.send(text_data=json.dumps({
            "action": "restore",
            "task_id": event["data"]["task_id"],
        }))

    async def file_update(self, event):
        await self.send(text_data=json.dumps({
            'action': 'file_update',
            'file_id': event['file_id'],
            'update_type': event['action'],
        }))

class ProjectListConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("projects", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("projects", self.channel_name)

    async def project_progress_update(self, event):
        await self.send(text_data=json.dumps({
            "action": "progress_update",
            "project_id": event["project_id"],
        }))

    async def project_update(self, event):
        await self.send(text_data=json.dumps({
            "action": event["action"],  # "create", "edit", "delete"
            "project_id": event["project_id"],
        }))

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.group_name = f'chat_{self.project_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        user = self.scope['user']
        message = data['message']
        # Save message to DB
        from .models import ChatMessage, Project
        project = await sync_to_async(Project.objects.get)(pk=self.project_id)
        await sync_to_async(ChatMessage.objects.create)(
            project=project, user=user, message=message
        )
        # Broadcast to group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'user': user.username,
                'message': message,
                'timestamp': str(datetime.datetime.now()),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'user': event['user'],
            'message': event['message'],
            'timestamp': event['timestamp'],
        }))