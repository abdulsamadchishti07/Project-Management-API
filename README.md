# TaskFlow API

A multi-tenant task/project management REST API built with FastAPI,
designed to practice production-level backend patterns.

## What it does

Users can create workspaces, invite members with specific roles
(owner/admin/member/viewer), organize work into projects, and manage
tasks with assignees, statuses, priorities, and comments. Access to
every resource is scoped to workspace membership and enforced by role.

## Why I built this

After completing a tutorial-based social media API, I wanted to build
something from documentation alone — no walkthroughs — to prove I
actually understand the concepts rather than just following along.
This project intentionally covers what tutorials usually skip:
role-based access control, multi-tenant data isolation, background
tasks, rate limiting, and caching.

## Tech stack

- FastAPI
- PostgreSQL + SQLAlchemy ORM
- Alembic (migrations)
- Redis (caching / rate limiting)
- JWT authentication
- Docker

## Core features

- JWT-based auth
- Workspace-scoped RBAC (owner/admin/member/viewer)
- Projects → Tasks → Comments hierarchy
- Background email notifications
- Redis caching + rate limiting
- Pagination, filtering, sorting on list endpoints
- Soft deletes with audit logging

## How to run it

### Option 1: Using Docker (Recommended)

1. Clone the repository and configure your environment:
   ```bash
   cp .env.example .env
   ```
2. Start the full stack (FastAPI + PostgreSQL + Redis):
   ```bash
   docker compose up --build
   ```
3. Open the interactive API documentation at:
   - **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### Option 2: Running Locally

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up your `.env` file with your PostgreSQL and Gmail SMTP credentials.

4. Run database migrations:

   ```bash
   alembic upgrade head
   ```

5. Start the development server:
   ```bash
   uvicorn app.main:app --reload
   ```
