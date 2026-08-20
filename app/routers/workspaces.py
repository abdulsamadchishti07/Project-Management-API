from typing import Annotated
from fastapi import Depends, status, HTTPException, APIRouter, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .. import model, schema, oauth2
from ..database import get_db
from ..rbac import Role, RequireWorkspaceRole

router = APIRouter(
    prefix="/workspace",
    tags=["Workspace"]
)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schema.WorkspaceOut)
def create_workspace(
    workspace: schema.WorkspaceCreate,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    new_workspace = model.Workspace(
        name=workspace.name,
        owner_id=current_user.id
    )
    db.add(new_workspace)
    db.commit()
    db.refresh(new_workspace)

    # Automatically add the creator as an 'Owner' member
    member = model.WorkspaceMember(
        user_id=current_user.id,
        workspace_id=new_workspace.id,
        role=Role.OWNER.value
    )
    db.add(member)
    db.commit()

    return new_workspace


@router.get("/", response_model=list[schema.WorkspaceOut])
def get_my_workspaces(
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Retrieves all workspaces the current user owns or is a member of."""
    member_workspace_ids = [
        row[0] for row in db.query(model.WorkspaceMember.workspace_id).filter(
            model.WorkspaceMember.user_id == current_user.id
        ).all()
    ]

    workspaces = db.query(model.Workspace).filter(
        or_(
            model.Workspace.owner_id == current_user.id,
            model.Workspace.id.in_(member_workspace_ids)
        )
    ).all()

    return workspaces


@router.get("/{workspace_id}", response_model=schema.WorkspaceOut)
def get_workspace(
    workspace_id: int,
    membership: Annotated[model.WorkspaceMember, Depends(RequireWorkspaceRole(Role.VIEWER))],
    db: Session = Depends(get_db)
):
    """Requires at least VIEWER role in the workspace."""
    workspace = db.query(model.Workspace).filter(model.Workspace.id == workspace_id).first()
    return workspace


@router.put("/{workspace_id}", response_model=schema.WorkspaceOut)
def update_workspace(
    workspace_id: int,
    workspace_data: schema.WorkspaceCreate,
    membership: Annotated[model.WorkspaceMember, Depends(RequireWorkspaceRole(Role.ADMIN))],
    db: Session = Depends(get_db)
):
    """Requires at least ADMIN or OWNER role in the workspace."""
    workspace_query = db.query(model.Workspace).filter(model.Workspace.id == workspace_id)
    workspace = workspace_query.first()

    workspace_query.update(workspace_data.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(workspace)

    return workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: int,
    membership: Annotated[model.WorkspaceMember, Depends(RequireWorkspaceRole(Role.OWNER))],
    db: Session = Depends(get_db)
):
    """Requires OWNER role to delete the workspace."""
    workspace = db.query(model.Workspace).filter(model.Workspace.id == workspace_id).first()

    db.delete(workspace)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
