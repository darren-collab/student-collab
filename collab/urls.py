from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .api_views import ProjectViewSet, TaskViewSet, ProjectFileViewSet, ChatMessageViewSet

# REST API Router
router = DefaultRouter()
router.register(r'api/projects', ProjectViewSet, basename='project-api')
router.register(r'api/tasks', TaskViewSet, basename='task-api')
router.register(r'api/files', ProjectFileViewSet, basename='file-api')
router.register(r'api/chat', ChatMessageViewSet, basename='chat-api')

urlpatterns = [
    
    path('', views.homepage, name='homepage'),
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('project/', views.project, name='project'),
    path('myTasks/', views.my_tasks, name='my_tasks'),
    path('userProfile/', views.user_profile, name='user_profile'),

    # Project management URLs
     path('projects/', views.project_list, name='project_list'),
    path('projects/add/', views.project_create, name='project_create'),
    path('projects/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('projects/<int:pk>/undelete/', views.project_undelete, name='project_undelete'),
    path('projects/<int:pk>/upload_file/', views.upload_file, name='upload_file'),
    path('projects/<int:pk>/delete_file/<int:file_id>/', views.delete_file, name='delete_file'),

    path('projects/<int:pk>/edit/json/', views.project_edit_json, name='project_edit_json'),

    # workspace URLs
    path('workspace/<int:pk>/', views.workspace, name='workspace'),
    path('workspace/<int:pk>/add_task/', views.add_task, name='add_task'),
   # path('tasks/<int:task_id>/update_status/', views.update_task_status, name='update_task_status'),
    path('tasks/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('tasks/<int:task_id>/restore/', views.restore_task, name='restore_task'),

    path('tasks/<int:task_id>/detail/', views.task_detail_json, name='task_detail_json'),
    path('tasks/<int:task_id>/edit/', views.edit_task, name='edit_task'),

    # profile URLs
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/change-password/', views.profile_change_password, name='profile_change_password'),

    path('logout/', views.logout_view, name='logout'),

] + router.urls