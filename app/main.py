from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_db_and_tables
from app.routers import auth, users, admin, student, debug
from app.config import get_settings

settings = get_settings()

# apka teraz sama stawia db jak nie istnieje 
# nie musisz tworzyc w psql samemu bazy
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="irss projekt do rekru",
    version="1.0.0",
    lifespan=lifespan,
    root_path="/api"
    )

origins = [
    "http://localhost", 
    "https://localhost", 
    "http://localhost:8080",
    "https://localhost:8080",
    "http://127.0.0.1",
    "https://127.0.0.1",
    "https://projektirss.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"], # Pozwalamy na GET, POST, PATCH
    allow_headers=["*"],
)

# ROUTERS
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(student.router)

if settings.DEBUG_MODE:
    app.include_router(debug.router)
    print(f"\n{'!'*40}")
    print("UWAGA: TRYB DEBUG WŁĄCZONY")
    print("Endpointy /debug są dostępne.")
    print(f"{'!'*40}\n") 

@app.get("/")
async def root():
    return {
        "message": f"{settings.APP_NAME} dziala :v",
        "status": "ok",
        "docs": "/docs",
    }
    
# do live reload serwera podczas edytowania
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG_MODE
    )