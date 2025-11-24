from fastapi import FastAPI

from database import engine
from models import Base
from routers import auth as auth_router
from routers import students as students_router

app = FastAPI(
    title="Students CRUD API with Auth",
    description="Домашнее задание: REST API + user_token/refresh авторизация",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


app.include_router(auth_router.router)
app.include_router(students_router.router)
