from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database import create_db_and_tables
from app.routers import auth, users, admin, student, debug
from app.config import get_settings

'''
TODO:
    > Zarządzanie kampaniami przez staroste
        > definiowanie grup i slotow
        > przy definitywnym zdefiniowaniu kampanii tworzy link dla userów
        > edycja ilosci miejsc w grupach
        > podgląd ile osob jest w danej grupie
    > Logika zapisu studenta
        > POST /student/register - wysyla wszsytkie group_id i priority
    > CORS
'''


settings = get_settings()

# apka teraz sama stawia db jak nie istnieje 
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="irss projekt do rekru",
    version="1.0.0",
    lifespan=lifespan
    )

# ROUTERS
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(student.router)
app.include_router(debug.router) # w production usunac/zakomentowac bo leak secretow 
# todo albo dodac env DEBUG_MODE i sprawdzac czy jest true to wtedy bedzie odpalac

@app.get("/")
async def root():
    return {
        "message": f"{settings.APP_NAME} dziala :v",
        "status": "ok",
        "docs": "/docs",
    }
    
# do live reload
# właczać w powershellu: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)