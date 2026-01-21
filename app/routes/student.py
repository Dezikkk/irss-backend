from fastapi import APIRouter
from pydantic import EmailStr
from app.database import SessionDep
from app.serializers.zapis import ZapisRequest, zapis_from_request
from app.utils.security import verify_email
from app.models.studia import get_studia_by_token

router = APIRouter(prefix="/student", tags=["student"])

@router.post("/verify/{email}")
def send_email_verification(email: EmailStr, session: SessionDep):
    # TODO: Implement email verification logic
    try:
        if verify_email():
            # Create password, add to database, send email
            return "cool"
    except Exception as e:
        return f"Failed to send verification email: {str(e)}"

@router.post("/priorities")
def get_student_priorities(request: ZapisRequest, session: SessionDep):
    # TODO: Implement logic for getting the priorities
    try:
        studia_id = get_studia_by_token(session, request.token)
        studia_id = 1
        if studia_id == None:
            raise Exception("bad token")
        zapis = zapis_from_request(studia_id, request)
        session.add(zapis)
        session.commit()
        session.refresh(zapis)
        return "{'message': 'cool'}"
    except Exception as e:
        return f"Failed to set priorities: {str(e)}"