from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import model, schema, utils, oauth2
from ..database import get_db

from typing import Annotated


router = APIRouter(
    prefix="/user",
    tags=["Users"]
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schema.UserOut)
def create_user(
    user: schema.UserCreate,
    db: Session = Depends(get_db)
):
    existing_email = db.query(model.Users).filter(model.Users.email == user.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user.email} already exists.",
        )

    hashed_password = utils.hash(user.password)
    user.password = hashed_password

    new_user = model.Users(**user.model_dump())

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/me", response_model=schema.UserOut)
def read_users_me(
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
):
    return current_user



@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schema.UserOut)
def create_user(
    user: schema.UserCreate,
    db: Session = Depends(get_db)
):
    existing_email = db.query(model.Users).filter(model.Users.email == user.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user.email} already exists.",
        )

    hashed_password = utils.hash(user.password)
    user.password = hashed_password

    new_user = model.Users(**user.model_dump())

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.get("/me", response_model=schema.UserOut)
def read_users_me(
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
):
    return current_user