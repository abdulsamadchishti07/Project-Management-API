from typing import Annotated, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status, HTTPException, Response, Query
from sqlalchemy.orm import Session

from .. import schema, model, oauth2
from ..database import get_db
from ..audit import log_activity
from ..rbac import Role, has_sufficient_role

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)


def verify_project_access(
    project_id: int,
    user_id: int, 
    db: Session,
    min_role: Role = Role.VIEWER
) -> model.Project:
    """Verifies that the project exists, user has access, and meets the minimum required role rank."""
    project = db.query(model.Project).filter(
        model.Project.id == project_id,
        model.Project.is_deleted == False
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Check workspace existence
    workspace = db.query(model.Workspace).filter(
        model.Workspace.id == project.workspace_id,
        model.Workspace.is_deleted == False
    ).first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent workspace not found"
        )

    # Determine user role in workspace
    if workspace.owner_id == user_id:
        user_role = Role.OWNER
    else:
        ws_member = db.query(model.WorkspaceMember).filter(
            model.WorkspaceMember.workspace_id == project.workspace_id,
            model.WorkspaceMember.user_id == user_id
        ).first()

        if not ws_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of the workspace this project belongs to"
            )
        user_role = ws_member.role

    # If project is private, check if user is the project owner or a project member
    if project.private:
        proj_member = db.query(model.ProjectMember).filter(
            model.ProjectMember.project_id == project.id,
            model.ProjectMember.user_id == user_id
        ).first()

        if project.owner_id != user_id and not proj_member and workspace.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this private project"
            )

    # Enforce RBAC Role Hierarchy
    if not has_sufficient_role(user_role, min_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Minimum role required: {min_role.value.capitalize()}."
        )

    return project


@router.post("/project/{project_id}", status_code=status.HTTP_201_CREATED, response_model=schema.TasksOut)
def create_task(
    project_id: int,
    task: schema.TasksCreate,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Requires at least MEMBER role to create a task."""
    project = verify_project_access(project_id=project_id, user_id=current_user.id, db=db, min_role=Role.MEMBER)

    # If assignee is provided, check if that user exists
    if task.assignee_id is not None:
        assignee = db.query(model.Users).filter(model.Users.id == task.assignee_id).first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignee with user id {task.assignee_id} does not exist"
            )

    new_task = model.Tasks(
        project_id=project_id,
        title=task.title,
        description=task.description,
        status=task.status or "pending",
        priority=task.priority or "medium",
        assignee_id=task.assignee_id,
        due_date=task.due_date
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    # Log Audit Activity
    log_activity(
        db=db,
        workspace_id=project.workspace_id,
        user_id=current_user.id,
        action="TASK_CREATED",
        entity_type="task",
        entity_id=new_task.id,
        details=f"Created task '{new_task.title}' with priority '{new_task.priority}'"
    )

    return new_task


@router.get("/project/{project_id}", response_model=list[schema.TasksOut])
def get_project_tasks(
    project_id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    priority_filter: Optional[str] = Query(default=None, alias="priority"),
    assignee_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
):
    """Requires at least VIEWER role to view project tasks."""
    verify_project_access(project_id=project_id, user_id=current_user.id, db=db, min_role=Role.VIEWER)

    query = db.query(model.Tasks).filter(
        model.Tasks.project_id == project_id,
        model.Tasks.is_deleted == False
    )

    if status_filter:
        query = query.filter(model.Tasks.status == status_filter)
    if priority_filter:
        query = query.filter(model.Tasks.priority == priority_filter)
    if assignee_id is not None:
        query = query.filter(model.Tasks.assignee_id == assignee_id)

    tasks = query.limit(limit).offset(offset).all()
    return tasks


@router.get("/{id}", response_model=schema.TasksOut)
def get_task(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Requires at least VIEWER role to view task details."""
    task = db.query(model.Tasks).filter(
        model.Tasks.id == id,
        model.Tasks.is_deleted == False
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {id} not found"
        )

    verify_project_access(project_id=task.project_id, user_id=current_user.id, db=db, min_role=Role.VIEWER)

    return task


@router.put("/{id}", response_model=schema.TasksOut)
def update_task(
    id: int,
    task_data: schema.TasksUpdate,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Requires at least MEMBER role to update a task."""
    task_query = db.query(model.Tasks).filter(
        model.Tasks.id == id,
        model.Tasks.is_deleted == False
    )
    task = task_query.first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {id} not found"
        )

    project = verify_project_access(project_id=task.project_id, user_id=current_user.id, db=db, min_role=Role.MEMBER)

    update_data = task_data.model_dump(exclude_unset=True)

    if "assignee_id" in update_data and update_data["assignee_id"] is not None:
        assignee = db.query(model.Users).filter(model.Users.id == update_data["assignee_id"]).first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignee with user id {update_data['assignee_id']} does not exist"
            )

    if update_data:
        task_query.update(update_data, synchronize_session=False)
        db.commit()
        db.refresh(task)

        # Log Audit Activity
        log_activity(
            db=db,
            workspace_id=project.workspace_id,
            user_id=current_user.id,
            action="TASK_UPDATED",
            entity_type="task",
            entity_id=task.id,
            details=f"Updated task '{task.title}' fields: {list(update_data.keys())}"
        )

    return task


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Requires at least ADMIN role or project creator to soft delete a task."""
    task = db.query(model.Tasks).filter(
        model.Tasks.id == id,
        model.Tasks.is_deleted == False
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {id} not found"
        )

    project = verify_project_access(project_id=task.project_id, user_id=current_user.id, db=db, min_role=Role.ADMIN)

    task_title = task.title

    # Soft delete
    task.is_deleted = True
    task.deleted_at = datetime.now(timezone.utc)
    db.commit()

    # Log Audit Activity
    log_activity(
        db=db,
        workspace_id=project.workspace_id,
        user_id=current_user.id,
        action="TASK_DELETED",
        entity_type="task",
        entity_id=id,
        details=f"Soft deleted task '{task_title}'"
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
