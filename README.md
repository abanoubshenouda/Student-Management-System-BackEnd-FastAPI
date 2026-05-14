# Student-Management-System-BackEnd-FastAPI

BackEnd FastAPI project for beginner level.

## Run

Install packages:

```bash
pip install -r requirements.txt
```

Run server:

```bash
uvicorn main:app --reload
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```

## Database

The database connection is in `database.py`.

Current database:

```text
Student_db
```

If your SQL Server name is different, change this part only:

```python
DESKTOP-4S17TOD\SQLEXPRESS
```

## Main Endpoints

Auth:

```text
POST /auth/register
POST /auth/login
```

Students:

```text
GET    /students/
GET    /students/{student_id}
POST   /students/
PUT    /students/{student_id}
DELETE /students/{student_id}
GET    /students/me
PUT    /students/me
```

Monitoring:

```text
GET /monitoring/audit-logs
GET /monitoring/dashboard
GET /monitoring/metrics
GET /monitoring/cache
GET /health
```

## Redis Caching

The API uses Redis cache for frequently accessed student reads:

```text
GET /students/
GET /students/{student_id}
```

The cache follows the cache-aside pattern: check Redis first, query the database on cache miss, store the result with a TTL, and invalidate student cache after create, update, or delete operations.

## Roles

Admin:

```text
Can create, read, update, delete all students.
Can see audit logs.
```

Student:

```text
Can see own profile.
Can update own profile.
Cannot access other students.
```

## Team Split

Member 1:

```text
Project setup, database.py, model.py, main.py, auth.py, dependencies.py
```

Member 2:

```text
Auth endpoints, register, login, JWT token, role check
```

Member 3:

```text
Student CRUD, filtering by department/GPA, pagination, student self profile
```

Member 4:

```text
Audit log, structured logging, Redis cache, monitoring endpoints/dashboard
```

Member 5:

```text
Testing, error handling review, README, Docker bonus
```

## Suggested Git Branches

```text
feature/project-setup-auth
feature/auth-rbac
feature/student-crud
feature/audit-cache-logging
feature/testing-docs
```

## Testing

Tests are organized in the `tests/` directory and use `pytest` with FastAPI `TestClient`.

Run:

```bash
pytest tests -v
```

## Docker

Run the complete stack:

```bash
docker compose up --build
```

Services:

```text
api    FastAPI application
db     SQL Server
redis  Redis cache
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```
