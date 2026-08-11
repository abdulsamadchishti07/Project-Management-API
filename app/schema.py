from datetime import datetime
from pydantic import EmailStr, BaseModel, Field

from pydantic import ConfigDict


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    active: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8, description="Password must be at least 8 characters")

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: int | None = None


# WorkSpace 

class WorkspaceCreate(BaseModel):
    name: str

class WorkspaceOut(BaseModel):
    id: int
    name: str
    active: bool
    created_at: datetime
    owner_id: int
    owner: UserOut 

    model_config = ConfigDict(from_attributes=True)

class WorkspaceMemberOut(BaseModel):
    id: int
    user_id: int
    workspace_id: int
    role: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)
class WorkspaceInvitationCreate(BaseModel):
    email: EmailStr
    role: str = "member"

class WorkspaceInviteOut(BaseModel):
    id: int
    workspace_id: int
    invited_email: EmailStr
    role: str
    status: str
    created_at: datetime
    invited_by: int
    model_config = ConfigDict(from_attributes=True)