from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse, Http404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, F, FloatField, Case, When, ExpressionWrapper
from django.db.models.functions import Lower
from collab.models import Project, Task
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from datetime import timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator  # add import
from django.contrib.auth import logout as auth_logout

from .models import Project,Task, ProjectFile
from .forms import ProjectForm, TaskForm

# Create your views here.

def homepage(request):
    return render(request, 'homepage.html')

# This view handles the dashboard page rendering
@login_required
def dashboard(request):
    # Projects the user created or is a team member of (active only via default manager)
    user_projects = Project.objects.filter(
        Q(created_by=request.user) | Q(team_members=request.user)
    ).distinct()

    # Latest 3 assigned tasks (exclude disabled), newest first
    latest_tasks = (
        Task.objects.filter(assigned_to=request.user, is_disabled=False, project__is_deleted=False )
        .select_related('project')
        .order_by('-id')[:3]  # use -created_at if you have it
    )

    # Task status (for current user, excluding disabled)
    user_tasks = Task.objects.filter(assigned_to=request.user, is_disabled=False, project__is_deleted=False )
    task_status = {
        "To-do": user_tasks.filter(status="todo").count(),
        "In Progress": user_tasks.filter(status="in_progress").count(),
        "Done": user_tasks.filter(status="done").count(),
    }
    # Task priority
    task_priority = {
        "Low": user_tasks.filter(priority="low").count(),
        "Medium": user_tasks.filter(priority="medium").count(),
        "High": user_tasks.filter(priority="high").count(),
    }
    # Project status (active projects the user is in)
    project_status = {
        "Planning": user_projects.filter(status="planning").count(),
        "In Progress": user_projects.filter(status="in_progress").count(),
        "Done": user_projects.filter(status="done").count(),
    }

    # Team workload (across the user's projects)
    teammates = (
        User.objects.filter(projects__in=user_projects)
        # .exclude(pk=request.user.pk)
        .distinct()
    )
    today = timezone.now().date()
    teammates_overview = []
    for tm in teammates:
        qs = Task.objects.filter(
            project__in=user_projects,
            assigned_to=tm,
            is_disabled=False,
        )
        total = qs.count()
        done = qs.filter(status='done').count()
        overdue = qs.filter(due_date__lt=today).exclude(status='done').count()
        percent_completed = int(done / total * 100) if total else 0
        teammates_overview.append({
            "id": tm.id,
            "name": tm.first_name or tm.username,
            "initials": (tm.first_name[:1] + tm.last_name[:1]).upper() if tm.first_name else tm.username[:2].upper(),
            "email": tm.email,
            "total": total,
            "done": done,
            "overdue": overdue,
            "percent": percent_completed,
            "is_you": tm.id == request.user.id, 
        })

    context = {
        "total_projects": user_projects.count(),
        "in_progress_projects": user_projects.filter(status="in_progress").count(),
        "completed_projects": user_projects.filter(status="done").count(),
        "latest_tasks": latest_tasks,
         # donut data bundle
        "chart_data": {
            "task_status": task_status,
            "task_priority": task_priority,
            "project_status": project_status,
        },
        "teammates_overview": teammates_overview,
    }
    return render(request, "dashboard_fyp.html", context)

# This view handles the project page rendering
@login_required
def project(request):
    projects = Project.objects.filter(team_members=request.user)
    project_progress_dict = {}
    team_members = User.objects.all()
    for project in projects:
        tasks = project.tasks.all()
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='done').count()
        progress = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
        project_progress_dict[project.id] = progress
    return render(request, 'projectTab_fyp.html', {
        'projects': projects,
        'team_members': team_members,
        'project_progress_dict': project_progress_dict,
    })

# login view
def login(request):
    context = {"show_signup": False}
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('pswd')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('dashboard')
        else:
            context["login_error"] = "Invalid credentials"
            
    return render(request, 'Login_Form.html',context)

# signup view
def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('pswd') or ''
        confirm_password = request.POST.get('confirm_pswd') or ''

        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'Login_Form.html', {'show_signup': True})

        # Enforce unique email (case-insensitive)
        if email and User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'Email already in use.')
            return render(request, 'Login_Form.html', {'show_signup': True})

        # Enforce unique username
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'Login_Form.html', {'show_signup': True})

        # Validate password using Django validators (similarity, length, common, numeric)
        try:
            dummy_user = User(username=username, email=email)
            validate_password(password, user=dummy_user)
        except ValidationError as e:
            for msg in e.messages:
                messages.error(request, msg)
            return render(request, 'Login_Form.html', {'show_signup': True})

        user = User.objects.create_user(
            username=username, email=email, password=password, first_name=username
        )
        user.save()
        messages.success(request, 'Account created. Please log in.')
        return redirect('login')

    return render(request, 'Login_Form.html', {'show_signup': True})


# Project management views

# This view lists all projects for the logged-in user
@login_required
def project_list(request):
    projects_qs = Project.objects.filter(
        team_members=request.user
    ).select_related('created_by').prefetch_related('team_members')

    # FILTER by status (planning | in_progress | done)
    status_param = request.GET.get('status')
    if status_param in ['planning', 'in_progress', 'done']:
        projects_qs = projects_qs.filter(status=status_param)

    # Annotate progress for sorting by progress (done / total * 100)
    projects_qs = projects_qs.annotate(
        total_tasks=Count('tasks', filter=Q(tasks__is_disabled=False)),
        done_tasks=Count('tasks', filter=Q(tasks__status='done', tasks__is_disabled=False)),
    ).annotate(
        progress_percent=Case(
            When(total_tasks=0, then=0),
            default=ExpressionWrapper(F('done_tasks') * 100.0 / F('total_tasks'), output_field=FloatField()),
            output_field=FloatField()
        )
    )

    # SORT (deadline | name | progress)
    sort_key = request.GET.get('sort', 'deadline')
    if sort_key == 'name':
        projects_qs = projects_qs.order_by(Lower('title'))
    elif sort_key == 'progress':
        # Descending progress
        projects_qs = projects_qs.order_by('-progress_percent', Lower('title'))
    else:  # deadline (default)
        projects_qs = projects_qs.order_by('due_date', Lower('title'))

    # PAGINATE after filter + sort
    page_number = request.GET.get('page', 1)
    paginator = Paginator(projects_qs, 4)
    projects = paginator.get_page(page_number)  # keep variable name

    # Progress dict (reuse annotated value)
    project_progress_dict = {}
    for p in projects:
        project_progress_dict[p.id] = int(p.progress_percent) if p.progress_percent is not None else 0

    cutoff = timezone.now() - timedelta(days=20)
    deleted_projects = (
        Project.objects_all
        .filter(is_deleted=True, deleted_at__gte=cutoff, team_members=request.user)
        .select_related('created_by')
        .prefetch_related('team_members')
    )

    now = timezone.now()
    days_left_by_id = {}
    for dp in deleted_projects:
        days_left = 20 - (now - dp.deleted_at).days if dp.deleted_at else 0
        days_left_by_id[dp.id] = max(0, days_left)

    return render(request, 'projectTab_fyp.html', {
        'projects': projects,
        'team_members': User.objects.all(),
        'project_progress_dict': project_progress_dict,
        'deleted_projects': deleted_projects,
        'days_left_by_id': days_left_by_id,
        'sort_key': sort_key,                 # NEW
        'status_param': status_param,
    })

# Function to broadcast project updates using WebSocket
def broadcast_project_update(action, project_id):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "projects",
        {
            "type": "project_update",
            "action": action,  # "create", "edit", "delete"
            "project_id": project_id,
        }
    )


# this view handles the creation of a new project
def project_create(request):
    form = ProjectForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
             # Ensure at least one team member selected
            team_members = form.cleaned_data.get('team_members')
            if not team_members:
                return HttpResponseBadRequest("Select a name.")
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            form.save_m2m()
            broadcast_project_update("create", project.id)
            return HttpResponse(status=200)
        else:
            return HttpResponseBadRequest("Invalid form data.")
    return HttpResponse("GET not supported", status=405)

# @login_required
# def project_create(request):
#     if request.method == 'POST':
#         form = ProjectForm(request.POST)
#         if form.is_valid():
#             project = form.save(commit=False)
#             project.created_by = request.user
#             project.save()
#             form.save_m2m()
#             return redirect('project_list')
#     else:
#         form = ProjectForm()
#     return render(request, 'projectTab_fyp.html', {'form': form})

# This view handles the editing of an existing project
@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user != project.created_by:
        return HttpResponseBadRequest("You do not have permission to edit this project.")
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == 'POST':
        if form.is_valid():
            project = form.save(commit=False)
            project.save()
            # Defensive: Only update team_members if present in POST
            if 'team_members' in request.POST:
                form.save_m2m()
            broadcast_project_update("edit", project.id)
            # else:
            #     # Do not clear team_members if not present
            #     pass
            return HttpResponse(status=200)
        else:
            html = render_to_string('project_form_fields.html', {'form': form})
            return HttpResponseBadRequest(html)
    html = render_to_string('project_form_fields.html', {'form': form})
    return HttpResponse(html)


# def project_edit(request, pk):
#     project = get_object_or_404(Project, pk=pk)
#     if request.user != project.created_by:
#         return redirect('project_list')
#     if request.method == 'POST':
#         form = ProjectForm(request.POST, instance=project)
#         if form.is_valid():
#             form.save()
#             return redirect('project_list')
#     else:
#         form = ProjectForm(instance=project)
#     return render(request, 'project_form_fields.html', {'form': form, 'edit': True})

#  This view handles the deletion of a project
@login_required
@require_POST
def project_delete(request, pk):
    project = get_object_or_404(Project.objects_all, pk=pk)  # include deleted rows
    if request.user != project.created_by:
        html = """
            <div style='padding:2rem; font-size:1.1rem; text-align:center;'>
                You do not have permission to delete this project. Only <strong>Project Creators</strong> can delete their projects.<br><br>
                <button onclick="document.getElementById('deleteProjectModal').style.display='none';" style='padding:0.5rem 2rem; border-radius:8px; background:#6366f1; color:white; border:none; font-size:1rem; cursor:pointer;'>OK</button>
            </div>
        """
        return HttpResponseBadRequest(html)

    project.soft_delete()
    broadcast_project_update("soft_delete", project.id)
    return HttpResponse("Soft-deleted")
    
# This view handles loading the workspace for a project
from collections import defaultdict

@login_required
def workspace(request, pk):
    project = get_object_or_404(Project, pk=pk)
    team_members = project.team_members.all()
    cutoff = timezone.now() - timedelta(days=2)

    tasks = project.tasks.select_related('assigned_to').exclude(is_disabled=True, disabled_at__lt=cutoff) .order_by('is_disabled', 'id')
    files = project.files.select_related('uploaded_by').all()
    chat_messages = project.chat_messages.order_by('timestamp')

    # Group files by name for versions tab
    file_versions = defaultdict(list)
    for f in files.order_by('name', '-version'):
        file_versions[f.name].append(f)
    file_versions = dict(file_versions) 

    active_tasks = tasks.filter(is_disabled=False)
    total_tasks = active_tasks.count()
    tot_completed_tasks = active_tasks.filter(status='done').count()
    project_progress_percent = int((tot_completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
    member_tasks = []
    for member in team_members:
        assigned_tasks = active_tasks.filter(assigned_to=member)
        total_member_tasks = assigned_tasks.count()
        completed_member_tasks = assigned_tasks.filter(status='done').count()
        member_progress = int((completed_member_tasks / total_member_tasks) * 100) if total_member_tasks > 0 else 0
        member_tasks.append({
            'member': member,
            'assigned_tasks': assigned_tasks,
            'progress': member_progress,

        })
    return render(request, 'workspace.html', {
        'project': project,
        'team_members': team_members,
        'tasks': tasks,
        'member_tasks': member_tasks,
        'project_progress_percent': project_progress_percent,
        'files': files,
        'file_versions': file_versions,
        'chat_messages': chat_messages,

    })


# def workspace(request, pk):
#     project = get_object_or_404(Project, pk=pk)
#     team_members = project.team_members.all()  # Assuming ManyToManyField
#     return render(request, 'workspace.html', {
#         'project': project,
#         'team_members': team_members,
#     })

# This view handles adding a new task to a project
@login_required
def add_task(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            task.save()

            # Notify all clients in the project group about the new task
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'project_{project.id}',
                {
                    'type': 'task_added',
                    'data': {
                        'task_id': task.id,
                        'name': task.name,
                        'description': task.description,
                        'due_date': str(task.due_date),
                        'assigned_to': task.assigned_to.username if task.assigned_to else '',
                        'status': task.status,
                    }
                }
            )

            # Notify all clients viewing the project list
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "projects",  # global group for project list
                {
                    "type": "project_progress_update",
                    "project_id": project.id,
                }
            )


            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


# no longer using this view; replaced by API View in api_views.py
# @login_required
# #@csrf_exempt  # Only if you have CSRF issues with AJAX; otherwise, keep CSRF protection
# def update_task_status(request, task_id):
#     if request.method == 'POST':
#         task = get_object_or_404(Task, id=task_id)
#         new_status = request.POST.get('status')
#         project_id = task.project.id  # Get the project ID
#         if new_status in ['todo', 'in_progress', 'done']:
#             task.status = new_status
#             task.save()

#             # Notify all clients in the project group about the status update
#             channel_layer = get_channel_layer()
#             async_to_sync(channel_layer.group_send)(
#                 f'project_{project_id}',
#                 {
#                     'type': 'task_update',
#                     'data': {
#                         'task_id': task_id,
#                         'status': new_status,
#                         # ...other task info...
#                     }
#                 }
#             )
#             # Notify all clients viewing the project list
#             channel_layer = get_channel_layer()
#             async_to_sync(channel_layer.group_send)(
#                 "projects",  # global group for project list
#                 {
#                     "type": "project_progress_update",
#                     "project_id": project_id,
#                 }
#             )

#             return JsonResponse({'success': True})
#     return JsonResponse({'success': False})

@login_required
@require_POST
def delete_task(request, task_id):
    # Soft-disable instead of hard delete
    task = get_object_or_404(Task, id=task_id)
    project_id = task.project.id
    if not task.is_disabled:
        task.is_disabled = True
        task.disabled_at = timezone.now()
        task.save(update_fields=['is_disabled', 'disabled_at'])

    channel_layer = get_channel_layer()
    # Notify workspace clients (optional real-time)
    async_to_sync(channel_layer.group_send)(
        f'project_{project_id}',
        {
            'type': 'task_disabled',
            'data': {'task_id': task_id}
        }
    )
    # Update project list progress (optional)
    async_to_sync(channel_layer.group_send)(
        "projects",
        {"type": "project_progress_update", "project_id": project_id}
    )

    return JsonResponse({'success': True, 'status': 'disabled'})

@login_required
@require_POST
def restore_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, is_disabled=True)
    project_id = task.project.id

    # Enforce 2-day restore window
    if task.disabled_at and timezone.now() - task.disabled_at > timedelta(days=2):
        return JsonResponse({'success': False, 'error': 'Restore window expired.'}, status=400)

    task.is_disabled = False
    task.disabled_at = None
    task.save(update_fields=['is_disabled', 'disabled_at'])

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'project_{project_id}',
        {
            'type': 'task_restored',
            'data': {'task_id': task_id}
        }
    )
    async_to_sync(channel_layer.group_send)(
        "projects",
        {"type": "project_progress_update", "project_id": project_id}
    )

    return JsonResponse({'success': True, 'status': 'restored'})

# File management views - upload files
@login_required
def upload_file(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        name = uploaded_file.name
        # Get latest version for this file name
        latest = ProjectFile.objects.filter(project=project, name=name).order_by('-version').first()
        version = latest.version + 1 if latest else 1
        pf = ProjectFile.objects.create(
            project=project,
            file=uploaded_file,
            uploaded_by=request.user,
            name=name,
            version=version
        )
        # Broadcast to all clients in this project
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{project.id}',
            {
                'type': 'file_update',
                'action': 'add',
                'file_id': pf.id,
            }
        )
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'No file uploaded'})

# File management views - delete files
@login_required
def delete_file(request, pk, file_id):
    project = get_object_or_404(Project, pk=pk)
    file = get_object_or_404(ProjectFile, pk=file_id, project=project)
    if request.method == 'POST':
        file.file.delete()
        file.delete()
        # Broadcast to all clients in this project
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{project.id}',
            {
                'type': 'file_update',
                'action': 'delete',
                'file_id': file_id,
            }
        )
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def my_tasks(request):
    # Get all tasks assigned to the current user, grouped by project
    tasks = Task.objects.filter(assigned_to=request.user,is_disabled=False, project__is_deleted=False).select_related('project')
    # Group tasks by project
    from collections import defaultdict
    project_tasks = defaultdict(list)
    for task in tasks:
        project_tasks[task.project].append(task)
    project_tasks = dict(project_tasks)

    return render(request, 'myTask_fyp.html', {
        'project_tasks': project_tasks,
    })

from django.http import JsonResponse, Http404
from .models import Project

def project_edit_json(request, pk):
    try:
        project = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        raise Http404("Project does not exist")

    data = {
        "title": project.title,
        "description": project.description,
        "due_date": project.due_date.isoformat() if project.due_date else "",
        "status": project.status,
        "team_members": list(project.team_members.values_list('id', flat=True)),
    }
    return JsonResponse(data)

@require_POST
@login_required
def project_undelete(request, pk):
    project = get_object_or_404(Project.objects_all, pk=pk, is_deleted=True)
    if request.user != project.created_by:
        return HttpResponseBadRequest("No permission to undelete.")

    if not project.deleted_at:
        return HttpResponseBadRequest("Not deleted.")
    if timezone.now() - project.deleted_at > timedelta(days=20):
        return HttpResponseBadRequest("Restore window expired.")

    project.undelete()
    broadcast_project_update("undelete", project.id)
    return HttpResponse("Restored")

@login_required
def user_profile(request):
    return render(request, 'userProfile.html', {
        'user': request.user,
    })

@login_required
@require_POST
def profile_update(request):
    user = request.user
    first_name = request.POST.get('first_name', '').strip()
    email = request.POST.get('email', '').strip()

    # Optional: enforce unique email
    if email and User.objects.exclude(pk=user.pk).filter(email=email).exists():
        return JsonResponse({'success': False, 'error': 'Email already in use.'}, status=400)

    user.first_name = first_name
    user.email = email
    user.save(update_fields=['first_name', 'email'])
    return JsonResponse({'success': True})

@login_required
@require_POST
def profile_change_password(request):
    user = request.user
    current = request.POST.get('current_password') or ''
    new1 = request.POST.get('new_password1') or ''
    new2 = request.POST.get('new_password2') or ''

    if not user.check_password(current):
        return JsonResponse({'success': False, 'error': 'Current password is incorrect.'}, status=400)
    if new1 != new2:
        return JsonResponse({'success': False, 'error': 'Passwords do not match.'}, status=400)
    try:
        validate_password(new1, user)
    except ValidationError as e:
        return JsonResponse({'success': False, 'errors': e.messages}, status=400)

    user.set_password(new1)
    user.save(update_fields=['password'])
    update_session_auth_hash(request, user)  # keep user logged in
    return JsonResponse({'success': True})


# View to get task details as JSON
@login_required
def task_detail_json(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    return JsonResponse({
        "id": task.id,
        "name": task.name,
        "description": task.description or "",
        "due_date": task.due_date.isoformat() if task.due_date else "",
        "priority": task.priority,
        "status": task.status,
        "assigned_to": task.assigned_to.username if task.assigned_to else "",
        "assigned_to_id": task.assigned_to.id if task.assigned_to else "",
        "project_id": task.project_id,
    })

# View to edit task details via POST
@login_required
@require_POST
def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    form = TaskForm(request.POST, instance=task)
    if form.is_valid():
        task = form.save()
        project_id = task.project_id

        # Broadcast to workspace viewers (same channel used elsewhere)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{project_id}',
            {
                'type': 'task_update',
                'data': {
                    'action': 'edit',
                    'task_id': task.id,
                    'name': task.name,
                    'description': task.description,
                    'due_date': task.due_date.isoformat() if task.due_date else '',
                    'assigned_to': task.assigned_to.username if task.assigned_to else '',
                    'assigned_to_id': task.assigned_to.id if task.assigned_to else '',
                    'status': task.status,
                    'priority': task.priority,
                }
            }
        )
        # Progress may change -> notify projects list listeners
        async_to_sync(channel_layer.group_send)(
            "projects",
            {"type": "project_progress_update", "project_id": project_id}
        )
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid data', 'errors': form.errors}, status=400)


@login_required
@require_POST
def logout_view(request):
    auth_logout(request)
    return redirect('login')