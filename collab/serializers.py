from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Project, Task, ProjectFile, ChatMessage


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class ProjectSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    team_members = UserSerializer(many=True, read_only=True)
    team_members_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        write_only=True,
        source='team_members'
    )
    
    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 'created_by', 'team_members',
            'team_members_ids', 'created_at', 'status', 'due_date',
            'is_deleted', 'deleted_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'is_deleted', 'deleted_at']


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True,
        source='assigned_to',
        allow_null=True,
        required=False
    )
    
    class Meta:
        model = Task
        fields = [
            'id', 'project', 'name', 'description', 'due_date',
            'assigned_to', 'assigned_to_id', 'status', 'priority',
            'created_at', 'is_disabled', 'disabled_at'
        ]
        read_only_fields = ['id', 'created_at', 'is_disabled', 'disabled_at']


class ProjectFileSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    
    class Meta:
        model = ProjectFile
        fields = ['id', 'project', 'file', 'uploaded_by', 'uploaded_at', 'name', 'version']
        read_only_fields = ['id', 'uploaded_by', 'uploaded_at', 'version']


class ChatMessageSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'project', 'user', 'message', 'timestamp']
        read_only_fields = ['id', 'user', 'timestamp']
