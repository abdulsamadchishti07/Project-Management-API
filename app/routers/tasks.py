from fastapi import APIRouter, Depends, status, HTTPException, Response, Query
from sqlalchemy.orm import Session

from .. import schema, model, oauth2
from ..database import get_db

from typing import Annotated, Optional


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)


def verify_project_access(
        project_id: int,
        user_id: int, 
        db: Session
) -> model.Project:
    
    project = db.query(model.Project).filter(model.Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Check workspace membership
    is_ws_member = db.query(model.WorkspaceMember).filter(
        model.WorkspaceMember.workspace_id == project.workspace_id,
        model.WorkspaceMember.user_id == user_id
    ).first()

    if not is_ws_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of the workspace this project belongs to"
        )

    # If project is private, check if user is the project owner or a project member
    if project.private:
        is_project_member = db.query(model.ProjectMember).filter(
            model.ProjectMember.project_id == project.id,
            model.ProjectMember.user_id == user_id
        ).first()

        if project.owner_id != user_id and not is_project_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this private project"
            )

    return project

@router.post("/project/{project_id}", status_code=status.HTTP_201_CREATED, response_model=schema.TasksOut)
def create_task(
    project_id: int,
    task: schema.TasksCreate,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    verify_project_access(project_id=project_id, user_id=current_user.id, db=db)

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
    verify_project_access(project_id=project_id, user_id=current_user.id, db=db)

    query = db.query(model.Tasks).filter(model.Tasks.project_id == project_id)

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
    task = db.query(model.Tasks).filter(model.Tasks.id == id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {id} not found"
        )

    verify_project_access(project_id=task.project_id, user_id=current_user.id, db=db)

    return task


@router.put("/{id}", response_model=schema.TasksOut)
def update_task(
    id: int,
    task_data: schema.TasksUpdate,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    task_query = db.query(model.Tasks).filter(model.Tasks.id == id)
    task = task_query.first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {id} not found"
        )

    verify_project_access(project_id=task.project_id, user_id=current_user.id, db=db)

    # Only update the fields that were provided in the request
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

    return task


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    task_query = db.query(model.Tasks).filter(model.Tasks.id == id)
    task = task_query.first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {id} not found"
        )

    verify_project_access(project_id=task.project_id, user_id=current_user.id, db=db)

    db.delete(task)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
