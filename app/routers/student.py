from fastapi import APIRouter

from app.core.dependencies import CurrentStudent

router = APIRouter(prefix="/student", tags=["Student"])

@router.get("/my-groups")
async def get_my_groups(current_user: CurrentStudent):
    """
    Zwraca grupy, do których student jest zapisany.
    Dostęp: Tylko Student.
    """
    # Logika wyciągania grup
    return {"message": "Tutaj będą Twoje grupy", "groups": []}