from typing import Annotated
from fastapi import Depends, status, HTTPException, APIRouter, Response
from sqlalchemy.orm import Session

from .. import model, schema, oauth2
from ..database import get_db

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

    # Automatically add the creator as an 'owner' member
    member = model.WorkspaceMember(
        user_id=current_user.id,
        workspace_id=new_workspace.id,
        role="owner"
    )
    db.add(member)
    db.commit()

    return new_workspace


@router.get("/{id}", response_model=schema.WorkspaceOut)
def get_workspace(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    workspace = db.query(model.Workspace).filter(model.Workspace.id == id).first()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with id {id} not found"
        )
    return workspace


@router.put("/{id}", response_model=schema.WorkspaceOut)
def update_workspace(
    id: int,
    workspace_data: schema.WorkspaceCreate,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    workspace_query = db.query(model.Workspace).filter(model.Workspace.id == id)
    workspace = workspace_query.first()

    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with id {id} not found"
        )
    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to perform this action"
        )

    workspace_query.update(workspace_data.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(workspace)

    return workspace


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    workspace = db.query(model.Workspace).filter(model.Workspace.id == id).first()

    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with id {id} not found"
        )
    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to perform this action"
        )

    db.delete(workspace)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
