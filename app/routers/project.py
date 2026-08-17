from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session

from .. import schema, model, oauth2
from ..database import get_db

from typing import Annotated


router = APIRouter(
    prefix=("/project"),
    tags=["Projects"]
)

@router.post("/workspace/{workspace_id}", status_code=status.HTTP_201_CREATED, response_model=schema.ProjectOut)
def create_project(
    workspace_id: int,
    project: schema.ProjectCreate,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    # Check if workspace exists
    workspace = db.query(model.Workspace).filter(model.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with id {workspace_id} not found"
        )

    new_project = model.Project(
        name=project.name,
        private=project.private if project.private is not None else False,
        workspace_id=workspace_id,
        owner_id=current_user.id
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    # Automatically add the creator as an 'Admin' in the project
    member = model.ProjectMember(
        user_id=current_user.id,
        project_id=new_project.id,
        role="Admin"
    )
    db.add(member)
    db.commit()

    return new_project


@router.get("/{id}", response_model=schema.ProjectOut)
def get_project(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    project = db.query(model.Project).filter(model.Project.id == id).first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {id} not found"
        )
    return project

@router.put("/{id}", response_model=schema.ProjectOut)
def update_project(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    project_data: schema.ProjectCreate,
    db: Session = Depends(get_db)
):

    project_query = db.query(model.Project).filter(model.Project.id == id)
    project = project_query.first()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {id} not found"
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code= status.HTTP_403_FORBIDDEN,
            detail=f"You are not allowed to performe this Action."
        )
    project_query.update(project_data.model_dump(), synchronize_session=False)

    db.commit()
    db.refresh(project)

    return project


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):

    project_query = db.query(model.Project).filter(model.Project.id == id)
    project = project_query.first()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {id} not found"
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code= status.HTTP_403_FORBIDDEN,
            detail=f"You are not allowed to performe this Action."

        )
    project_query.delete( synchronize_session=False)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
