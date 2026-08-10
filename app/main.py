from fastapi import FastAPI
from .routers import auth, users


app = FastAPI()

app.include_router(users.router)
app.include_router(auth.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}  