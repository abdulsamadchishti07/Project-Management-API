from typing import Annotated
from fastapi import APIRouter, Depends, status, HTTPException, Response, BackgroundTasks

from sqlalchemy.orm import Session
from .. import schema, model, oauth2, email

from ..database import get_db
from ..rbac import Role, RequireWorkspaceRole

from .tasks import verify_project_access

router = APIRouter(
    prefix="/invitations",
    tags=["Invitations"]
)


@router.post("/workspace/{workspace_id}", status_code=status.HTTP_201_CREATED, response_model=schema.WorkspaceInviteOut)
def invite_to_workspace(
    workspace_id: int,
    invitation_data: schema.WorkspaceInvitationCreate,
    background_tasks: BackgroundTasks,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    membership: Annotated[model.WorkspaceMember, Depends(RequireWorkspaceRole(Role.ADMIN))],
    db: Session = Depends(get_db)
):
    """Requires at least ADMIN or OWNER role in the workspace to send invites."""
    workspace = db.query(model.Workspace).filter(model.Workspace.id == workspace_id).first()

    # Check if invited user is already a member
    invited_user = db.query(model.Users).filter(model.Users.email == invitation_data.email).first()
    if invited_user:
        already_member = db.query(model.WorkspaceMember).filter(
            model.WorkspaceMember.workspace_id == workspace_id,
            model.WorkspaceMember.user_id == invited_user.id
        ).first()
        if already_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email {invitation_data.email} is already a member of this workspace"
            )

    # Check if there is already a pending invite
    pending_invite = db.query(model.WorkspaceInvitation).filter(
        model.WorkspaceInvitation.workspace_id == workspace_id,
        model.WorkspaceInvitation.invited_email == invitation_data.email,
        model.WorkspaceInvitation.status == "pending"
    ).first()

    if pending_invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An active invitation for {invitation_data.email} is already pending"
        )

    new_invite = model.WorkspaceInvitation(
        workspace_id=workspace_id,
        invited_email=invitation_data.email,
        invited_by=current_user.id,
        role=invitation_data.role,
        status="pending"
    )

    db.add(new_invite)
    db.commit()
    db.refresh(new_invite)

    # Send invitation email in the background
    background_tasks.add_task(
        email.send_invitation_email,
        to_email=new_invite.invited_email,
        workspace_name=workspace.name,
        role=new_invite.role,
        inviter_name=current_user.name
    )

    return new_invite


@router.get("/me", response_model=list[schema.WorkspaceInviteOut])
def get_my_invitations(
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Retrieves all pending workspace invitations sent to the current user's email."""
    invitations = db.query(model.WorkspaceInvitation).filter(
        model.WorkspaceInvitation.invited_email == current_user.email,
        model.WorkspaceInvitation.status == "pending"
    ).all()

    return invitations


@router.post("/workspace/{id}/accept", response_model=schema.MessageResponse)
def accept_workspace_invitation(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    invite = db.query(model.WorkspaceInvitation).filter(
        model.WorkspaceInvitation.id == id,
        model.WorkspaceInvitation.status == "pending"
    ).first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending invitation not found"
        )

    if invite.invited_email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was not sent to your email address"
        )

    # Add user as member
    new_member = model.WorkspaceMember(
        user_id=current_user.id,
        workspace_id=invite.workspace_id,
        role=invite.role
    )
    db.add(new_member)

    # Mark invite as accepted
    invite.status = "accepted"
    db.commit()

    return {"message": f"Invitation accepted! You are now a {invite.role} in this workspace."}


@router.post("/workspace/{id}/reject", response_model=schema.MessageResponse)
def reject_workspace_invitation(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    invite = db.query(model.WorkspaceInvitation).filter(
        model.WorkspaceInvitation.id == id,
        model.WorkspaceInvitation.status == "pending"
    ).first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending invitation not found"
        )

    if invite.invited_email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was not sent to your email address"
        )

    invite.status = "rejected"
    db.commit()

    return {"message": "Invitation declined."}


@router.post("/project/{project_id}", status_code=status.HTTP_201_CREATED, response_model=schema.ProjectInviteOut)
def invite_to_project(
    project_id: int,
    invitation_data: schema.ProjectInvitationCreate,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    project = verify_project_access(project_id=project_id, user_id=current_user.id, db=db, min_role=Role.ADMIN)

    # Check if target user is in the parent workspace first
    target_user = db.query(model.Users).filter(model.Users.email == invitation_data.email).first()
    if target_user:
        is_ws_member = db.query(model.WorkspaceMember).filter(
            model.WorkspaceMember.workspace_id == project.workspace_id,
            model.WorkspaceMember.user_id == target_user.id
        ).first()

        if not is_ws_member and project.owner_id != target_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be a member of the workspace before joining a private project"
            )

    new_invite = model.ProjectInvitation(
        project_id=project_id,
        invited_email=invitation_data.email,
        invited_by=current_user.id,
        role=invitation_data.role,
        status="pending"
    )

    db.add(new_invite)
    db.commit()
    db.refresh(new_invite)

    return new_invite


@router.post("/project/{id}/accept", response_model=schema.MessageResponse)
def accept_project_invitation(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    invite = db.query(model.ProjectInvitation).filter(
        model.ProjectInvitation.id == id,
        model.ProjectInvitation.status == "pending"
    ).first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending project invitation not found"
        )

    if invite.invited_email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was not sent to your email address"
        )

    new_member = model.ProjectMember(
        user_id=current_user.id,
        project_id=invite.project_id,
        role=invite.role
    )
    db.add(new_member)

    invite.status = "accepted"
    db.commit()

    return {"message": f"Project invitation accepted! You now have access to this project."}
