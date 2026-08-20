from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import database, model, oauth2, schema, utils
from ..redis_client import RateLimiter

router = APIRouter(
    tags=["Authentication"]
)


@router.post(
    "/login",
    response_model=schema.Token, 
    dependencies=[
        Depends(
            RateLimiter(
                times=5, 
                seconds=60, 
                key_prefix="rate_login"
            )
        )
    ]
)
def login(
    user_credential: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(database.get_db),
):
    user = db.query(model.Users).filter(model.Users.email == user_credential.username).first()

    if not user or not utils.verify_password(user_credential.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email with the OTP code before logging in."
        )

    access_token = oauth2.create_access_token(data={"user_id": user.id, "sub": str(user.id)})

    return {"access_token": access_token, "token_type": "bearer"}


