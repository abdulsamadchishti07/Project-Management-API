from datetime import datetime
from pydantic import EmailStr, BaseModel, Field

from pydantic import ConfigDict
from typing import Optional

    # User
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

    # Token
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

    # project

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    private: Optional[bool] = False

class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    active: bool
    created_at: datetime
    private: bool
    owner_id: int
    owner: UserOut 
    workspace_id: int

    model_config = ConfigDict(from_attributes=True)

class ProjectInvitationCreate(BaseModel):
    email: EmailStr
    project_id: int
    role: str = "member"

class ProjectInviteOut(BaseModel):
    id: int
    project_id: int
    invited_email: EmailStr
    role: str
    status: str
    created_at: datetime
    invited_by: int

    model_config = ConfigDict(from_attributes=True)

# task

class TasksCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "pending"
    priority: Optional[str] = "medium"
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None

class TasksUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None

class TasksOut(BaseModel):
    id: int
    project_id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    assignee_id: Optional[int] = None
    assignee: Optional[UserOut] = None
    created_at: datetime
    due_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# comments

class CommentsCreate(BaseModel):
    content: str

class CommentsOut(BaseModel):
    id: int
    task_id: int
    user_id: int
    user: Optional[UserOut] = None
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
