from fastapi import APIRouter

from app.core.dependencies import CurrentUser

router = APIRouter(prefix="/student", tags=["Student"])

@router.get("/my-groups")
async def get_my_groups(current_user: CurrentUser):
    """
    Zwraca grupy, do których student jest zapisany.
    """
    # Logika wyciągania grup
    return {"message": "Tutaj będą Twoje grupy", "groups": []}