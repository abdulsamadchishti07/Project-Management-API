from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session

from .. import schema, model, oauth2
from ..database import get_db

from typing import Annotated, Optional
from sqlalchemy import or_


router = APIRouter(
    prefix="/project",
    tags=["Projects"]
)


def verify_workspace_membership(
    workspace_id: int, 
    user_id: int, 
    db: Session
) -> model.Workspace:

    workspace = db.query(model.Workspace).filter(model.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with id {workspace_id} not found"
        )

    is_member = db.query(model.WorkspaceMember).filter(
        model.WorkspaceMember.workspace_id == workspace_id,
        model.WorkspaceMember.user_id == user_id
    ).first()

    if not is_member and workspace.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace"
        )

    return workspace


@router.post("/workspace/{workspace_id}", status_code=status.HTTP_201_CREATED, response_model=schema.ProjectOut)
def create_project(
    workspace_id: int,
    project: schema.ProjectCreate,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    # Verify user is a member of the workspace
    verify_workspace_membership(workspace_id=workspace_id, user_id=current_user.id, db=db)

    new_project = model.Project(
        name=project.name,
        description=project.description,
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


@router.get("/workspace/{workspace_id}", response_model=list[schema.ProjectOut])
def get_workspace_projects(
    workspace_id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    # Verify user is a member of the workspace
    verify_workspace_membership(workspace_id=workspace_id, user_id=current_user.id, db=db)

    # Fetch IDs of private projects where the current user is a member
    member_project_ids = [
        row[0] for row in db.query(model.ProjectMember.project_id).filter(
            model.ProjectMember.user_id == current_user.id
        ).all()
    ]

    # Return public projects OR private projects owned by user OR private projects where user is a member
    projects = db.query(model.Project).filter(
        model.Project.workspace_id == workspace_id,
        or_(
            model.Project.private == False,
            model.Project.owner_id == current_user.id,
            model.Project.id.in_(member_project_ids)
        )
    ).all()

    return projects


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

    # Check if user is a member of the parent workspace
    verify_workspace_membership(workspace_id=project.workspace_id, user_id=current_user.id, db=db)

    # Privacy check for private projects
    if project.private:
        is_project_member = db.query(model.ProjectMember).filter(
            model.ProjectMember.project_id == project.id,
            model.ProjectMember.user_id == current_user.id
        ).first()

        if project.owner_id != current_user.id and not is_project_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this private project"
            )

    return project

@router.put("/{id}", response_model=schema.ProjectOut)
def update_project(
    id: int,
    project_data: schema.ProjectCreate,
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to perform this action."
        )

    update_dict = project_data.model_dump(exclude_unset=True)
    if update_dict:
        project_query.update(update_dict, synchronize_session=False)
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to perform this action."
        )

    db.delete(project)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
