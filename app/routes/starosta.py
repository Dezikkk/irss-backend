from fastapi import APIRouter
from app.database import SessionDep
from app.serializers.studia import StudiaRequest, studia_from_request

router = APIRouter(prefix="/starosta", tags=["starosta"])

# Create a new row in the 'studia' table through a json request
# It requires a password previously present in the 'hasla' table
@router.post("/submit")
def submit_studia(request: StudiaRequest, session: SessionDep):
    try:
        studia = studia_from_request(request)
        session.add(studia)
        session.commit()
        session.refresh(studia)
        return "cool"
    except Exception as e:
        return f"Failed to create studia: {str(e)}"