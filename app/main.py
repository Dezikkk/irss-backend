from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import create_db_and_tables
from app.routes import starosta, student

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(starosta.router)
app.include_router(student.router)

@app.get("/")
def read_root():
    return {"message": "el huevo"}