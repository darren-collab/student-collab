from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class ProjectQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)
    def deleted(self):
        return self.filter(is_deleted=True)
    def ready_for_purge(self, days=20):
        cutoff = timezone.now() - timedelta(days=days)
        return self.deleted().filter(deleted_at__lt=cutoff)

class ProjectManager(models.Manager):
    def get_queryset(self):
        return ProjectQuerySet(self.model, using=self._db).active()

class Project(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects')
    team_members = models.ManyToManyField(User, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    due_date = models.DateField(null=True, blank=True)  # Optional
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = ProjectManager()             # active only
    objects_all = models.Manager()         # all rows (incl. deleted)

    # Helpers
    def soft_delete(self):
        if not self.is_deleted:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save(update_fields=['is_deleted', 'deleted_at'])

    def undelete(self):
        if self.is_deleted:
            self.is_deleted = False
            self.deleted_at = None
            self.save(update_fields=['is_deleted', 'deleted_at'])

    def __str__(self):
        return self.title

    def get_progress_percentage(self):
        if self.status == 'done':
            return 100
        elif self.status == 'in_progress':
            return 50
        return 25

class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('todo', 'To Do'), ('in_progress', 'In Progress'), ('done', 'Done')], default='todo')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')  # <-- Add this line
    created_at = models.DateTimeField(auto_now_add=True)


    is_disabled = models.BooleanField(default=False, db_index=True)
    disabled_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.name

class ProjectFile(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='project_files/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255)  # Display name
    version = models.IntegerField(default=1)  # Add this line

    def __str__(self):
        return f"{self.name} (v{self.version})"

class ChatMessage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='chat_messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    