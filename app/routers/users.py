from fastapi import APIRouter, Depends, HTTPException, status, Response
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
def read_user_me(
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
):
    return current_user

@router.get("/{id}", response_model=schema.UserOut)
def get_user(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    user = db.query(model.Users).filter(model.Users.id == id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail= f"User with this id {id} does not exist"
        )
    return user


@router.put("/{id}", response_model=schema.UserOut)
def update_user(
    id: int,
    user_update: schema.UserCreate,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    user_query = db.query(model.Users).filter(model.Users.id == id)
    user = user_query.first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {id} does not exist"
        )
        
    if user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to perform this Action."
        )

    #  Check if new email is already taken by another user or not
    if user_update.email != user.email:
        email_taken = db.query(model.Users).filter(model.Users.email == user_update.email).first()
        if email_taken:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email {user_update.email} is already in use by another account."
            )

    # Hash the new password before saving
    update_data = user_update.model_dump()
    update_data["password"] = utils.hash(update_data["password"])

    user_query.update(update_data, synchronize_session=False)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    id: int,
    current_user: Annotated[model.Users, Depends(oauth2.get_current_active_user)],
    db: Session = Depends(get_db)
):
    user = db.query(model.Users).filter(model.Users.id == id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {id} does not exist"
        )
    if user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to perform this Action."
        )
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)