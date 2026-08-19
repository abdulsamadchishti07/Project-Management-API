from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session

from typing import Annotated
from .. import schema, model, oauth2

from .tasks import verify_project_access
from ..database import get_db

router = APIRouter(
    prefix="/comments",
    tags=["Comments"]
)


def verify_task_access(task_id: int, user_id: int, db: Session) -> model.Tasks:
    """Helper to verify that a task exists and the user has access to its project."""
    task = db.query(model.Tasks).filter(model.Tasks.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

    # Verify user has access to the parent project and workspace
    verify_project_access(project_id=task.project_id, user_id=user_id, db=db)

    return task


@router.post("/task/{task_id}", status_code=status.HTTP_201_CREATED, response_model=schema.CommentsOut)
def create_comment(
    task_id: int,
    comment_data: schema.CommentsCreate,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    verify_task_access(task_id=task_id, user_id=current_user.id, db=db)

    new_comment = model.Comments(
        task_id=task_id,
        user_id=current_user.id,
        content=comment_data.content
    )

    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return new_comment


@router.get("/task/{task_id}", response_model=list[schema.CommentsOut])
def get_task_comments(
    task_id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    verify_task_access(task_id=task_id, user_id=current_user.id, db=db)

    comments = db.query(model.Comments).filter(
        model.Comments.task_id == task_id
    ).order_by(model.Comments.created_at.asc()).all()

    return comments


@router.put("/{id}", response_model=schema.CommentsOut)
def update_comment(
    id: int,
    comment_data: schema.CommentsCreate,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    comment_query = db.query(model.Comments).filter(model.Comments.id == id)
    comment = comment_query.first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id {id} not found"
        )

    # Verify task access
    verify_task_access(task_id=comment.task_id, user_id=current_user.id, db=db)

    # Only the author can edit their comment
    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to edit this comment"
        )

    comment_query.update(comment_data.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(comment)

    return comment


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    comment = db.query(model.Comments).filter(model.Comments.id == id).first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id {id} not found"
        )

    # Verify task access
    task = verify_task_access(task_id=comment.task_id, user_id=current_user.id, db=db)

    # Allowed if the user is the comment author OR the project owner
    project = db.query(model.Project).filter(model.Project.id == task.project_id).first()
    is_project_owner = project and project.owner_id == current_user.id

    if comment.user_id != current_user.id and not is_project_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete this comment"
        )

    db.delete(comment)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
