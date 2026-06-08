# CollabSpace API Documentation

## Overview
CollabSpace now includes a fully functional REST API built with Django REST Framework. This API allows programmatic access to all core resources: Projects, Tasks, Files, and Chat Messages.

## Base URL
```
http://localhost:8000/api/
```

## Authentication
All API endpoints require authentication. Use Django's Token Authentication or Session Authentication.

---

## Endpoints

### 1. Projects API

#### List Projects
- **Endpoint:** `GET /api/projects/`
- **Description:** Get all projects the user is involved with
- **Response:** List of projects with full details

**Example Request:**
```bash
curl -H "Authorization: Token YOUR_TOKEN" http://localhost:8000/api/projects/
```

**Example Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Mobile App Redesign",
      "description": "Redesign the mobile application UI/UX",
      "created_by": {
        "id": 1,
        "username": "john_dev",
        "email": "john@example.com",
        "first_name": "John"
      },
      "team_members": [...],
      "created_at": "2026-01-10T10:30:00Z",
      "status": "in_progress",
      "due_date": "2026-02-15",
      "is_deleted": false
    }
  ]
}
```

#### Create Project
- **Endpoint:** `POST /api/projects/`
- **Description:** Create a new project
- **Request Body:**
```json
{
  "title": "New Project",
  "description": "Project description",
  "status": "planning",
  "due_date": "2026-03-01",
  "team_members_ids": [1, 2, 3]
}
```

#### Get Project Details
- **Endpoint:** `GET /api/projects/{id}/`
- **Description:** Get details of a specific project

#### Update Project
- **Endpoint:** `PUT /api/projects/{id}/`
- **Description:** Update an existing project

#### Delete Project (Soft Delete)
- **Endpoint:** `DELETE /api/projects/{id}/`
- **Description:** Soft delete a project

#### Add Team Member
- **Endpoint:** `POST /api/projects/{id}/add_team_member/`
- **Request Body:**
```json
{
  "user_id": 5
}
```

---

### 2. Tasks API

#### List Tasks
- **Endpoint:** `GET /api/tasks/`
- **Description:** Get all tasks assigned to user or in their projects
- **Response:** List of tasks with full details

**Example Request:**
```bash
curl -H "Authorization: Token YOUR_TOKEN" http://localhost:8000/api/tasks/
```

**Example Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "project": 1,
      "name": "Design database schema",
      "description": "Create the database schema for user management",
      "due_date": "2026-01-20",
      "assigned_to": {
        "id": 2,
        "username": "jane_dev",
        "email": "jane@example.com"
      },
      "status": "in_progress",
      "priority": "high",
      "created_at": "2026-01-10T10:30:00Z",
      "is_disabled": false
    }
  ]
}
```

#### Create Task
- **Endpoint:** `POST /api/tasks/`
- **Request Body:**
```json
{
  "project": 1,
  "name": "Implement API authentication",
  "description": "Add JWT token authentication",
  "status": "todo",
  "priority": "high",
  "due_date": "2026-02-01",
  "assigned_to_id": 2
}
```

#### Update Task Status
- **Endpoint:** `POST /api/tasks/{id}/update_status/`
- **Request Body:**
```json
{
  "status": "done"
}
```
- **Valid statuses:** `todo`, `in_progress`, `done`

#### Mark Task as Complete
- **Endpoint:** `POST /api/tasks/{id}/mark_complete/`
- **Description:** Quickly mark a task as done

#### Get Task Details
- **Endpoint:** `GET /api/tasks/{id}/`

#### Update Task
- **Endpoint:** `PUT /api/tasks/{id}/`

#### Delete Task (Soft Disable)
- **Endpoint:** `DELETE /api/tasks/{id}/`

---

### 3. Files API

#### List Project Files
- **Endpoint:** `GET /api/files/`
- **Description:** Get all files in user's projects

#### Upload File
- **Endpoint:** `POST /api/files/`
- **Request:** Multipart form data with `file`, `project`, and `name` fields

#### Get File Details
- **Endpoint:** `GET /api/files/{id}/`

#### Delete File
- **Endpoint:** `DELETE /api/files/{id}/`

---

### 4. Chat Messages API

#### List Chat Messages
- **Endpoint:** `GET /api/chat/`
- **Description:** Get all chat messages in user's projects
- **Query Parameters:** 
  - `project` - Filter by project ID

#### Send Chat Message
- **Endpoint:** `POST /api/chat/`
- **Request Body:**
```json
{
  "project": 1,
  "message": "Great progress on the API implementation!"
}
```

#### Get Message Details
- **Endpoint:** `GET /api/chat/{id}/`

---

## Status Codes

- `200 OK` - Successful GET, PUT, or POST request
- `201 Created` - Resource successfully created
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - User lacks permission
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Testing the API

### Using cURL
```bash
# Get projects
curl -H "Authorization: Token YOUR_TOKEN" http://localhost:8000/api/projects/

# Create a project
curl -X POST http://localhost:8000/api/projects/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"New Project","status":"planning"}'
```

### Using Postman
1. Import the API endpoints
2. Set up authentication headers
3. Test each endpoint

### Using Python
```python
import requests

headers = {'Authorization': 'Token YOUR_TOKEN'}

# Get projects
response = requests.get('http://localhost:8000/api/projects/', headers=headers)
projects = response.json()
print(projects)

# Create task
task_data = {
    'project': 1,
    'name': 'New Task',
    'status': 'todo',
    'priority': 'medium'
}
response = requests.post('http://localhost:8000/api/tasks/', json=task_data, headers=headers)
print(response.json())
```

---

## API Features

✅ **Full CRUD Operations** - Create, Read, Update, Delete for all resources
✅ **Authentication** - Secure endpoints with token/session auth
✅ **Filtering & Permissions** - Users only see their own data
✅ **Nested Relationships** - Full user details in responses
✅ **Custom Actions** - Additional endpoints like `mark_complete`, `add_team_member`
✅ **Error Handling** - Proper HTTP status codes and error messages
✅ **Pagination** - Large result sets are automatically paginated

---

## Getting a Token (Optional)

If you want to use Token Authentication:

```bash
# Create a token for a user
python manage.py drf_create_token username

# Or via API if you set up authentication endpoint
curl -X POST http://localhost:8000/api-token-auth/ \
  -d "username=john&password=password123"
```
