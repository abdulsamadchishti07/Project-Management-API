from datetime import datetime
from pydantic import EmailStr, BaseModel, Field


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    active: bool = True
    created_at: datetime

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8, description="Password must be at least 8 characters")