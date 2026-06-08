from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Project, Task, ProjectFile, ChatMessage
from .serializers import (
    ProjectSerializer, TaskSerializer, ProjectFileSerializer,
    ChatMessageSerializer
)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint for projects.
    - GET /api/projects/ - List all projects (user is team member of)
    - POST /api/projects/ - Create new project
    - GET /api/projects/{id}/ - Get project details
    - PUT /api/projects/{id}/ - Update project
    - DELETE /api/projects/{id}/ - Delete (soft delete) project
    """
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only show projects the user is involved with
        return Project.objects.filter(
            team_members=self.request.user
        ) | Project.objects.filter(
            created_by=self.request.user
        )

    def perform_create(self, serializer):
        # Set creator as current user
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def add_team_member(self, request, pk=None):
        """Add a team member to the project"""
        project = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.contrib.auth.models import User
        user = get_object_or_404(User, pk=user_id)
        project.team_members.add(user)
        
        return Response(
            {'status': 'team member added'},
            status=status.HTTP_200_OK
        )


class TaskViewSet(viewsets.ModelViewSet):
    """
    API endpoint for tasks.
    - GET /api/tasks/ - List all tasks (assigned to user)
    - POST /api/tasks/ - Create new task
    - GET /api/tasks/{id}/ - Get task details
    - PUT /api/tasks/{id}/ - Update task
    - DELETE /api/tasks/{id}/ - Delete (soft disable) task
    """
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Show tasks assigned to user or in projects they're in
        from django.db.models import Q
        return Task.objects.filter(
            Q(assigned_to=self.request.user) |
            Q(project__team_members=self.request.user) |
            Q(project__created_by=self.request.user)
        ).distinct()

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update task status"""
        task = self.get_object()
        new_status = request.data.get('status')
        
        valid_statuses = ['todo', 'in_progress', 'done']
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.status = new_status
        task.save()
        
        # Broadcast update using existing task_update event type
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{task.project_id}',
            {
                'type': 'task_update',
                'data': {
                    'task_id': task.id,
                    'status': new_status
                }
            }
        )
        
        return Response(
            TaskSerializer(task).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def mark_complete(self, request, pk=None):
        """Mark task as complete"""
        task = self.get_object()
            #task.status = 'done'
            #task.save()
        new_status = request.data.get('status')
        if new_status in ['todo', 'in_progress', 'done']:
                task.status = new_status
                task.save()
            # Broadcast update to WebSocket clients
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
                f'project_{task.project_id}',
                {
                    'type': 'task_update',
                    'data': {
                        'task_id': task.id,
                        'status': new_status,
                    }
                }
            )
        
        return Response(
            TaskSerializer(task).data,
            status=status.HTTP_200_OK
        )


class ProjectFileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for project files.
    - GET /api/files/ - List all files
    - POST /api/files/ - Upload new file
    - GET /api/files/{id}/ - Get file details
    - DELETE /api/files/{id}/ - Delete file
    """
    serializer_class = ProjectFileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProjectFile.objects.filter(
            project__team_members=self.request.user
        )


class ChatMessageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for chat messages.
    - GET /api/chat/ - List all messages
    - POST /api/chat/ - Create new message
    - GET /api/chat/{id}/ - Get message details
    """
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ChatMessage.objects.filter(
            project__team_members=self.request.user
        )

    def perform_create(self, serializer):
        # Set user as current user
        serializer.save(user=self.request.user)
