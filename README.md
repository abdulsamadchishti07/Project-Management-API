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