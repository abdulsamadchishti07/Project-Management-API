from typing import Annotated, Optional
from fastapi import FastAPI, Depends
from .routers import auth, users, workspaces, project, tasks, comments, invitations
from . import model, oauth2

app = FastAPI()

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(project.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(invitations.router)


@app.get("/")
def root(current_user: Annotated[Optional[model.Users], Depends(oauth2.get_optional_current_user)] = None):
    if current_user is None:
        return {"message": "Welcome to TaskFlow!"}
    return {"message": f"Welcome to TaskFlow, {current_user.name}!"}
