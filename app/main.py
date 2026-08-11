from fastapi import FastAPI
from .routers import auth, users, workspaces


app = FastAPI()

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(workspaces.router)




@app.get("/")
async def root():
    return {"message": "Hello World"}