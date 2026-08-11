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