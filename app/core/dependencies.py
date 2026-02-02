from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlmodel import select

from app.models.models import UserRole
from app.config import get_settings
from app.database import SessionDep
from app.models.models import User

settings = get_settings()

# typ autoryzacji aplikacji, w swagger (localhost:8000/docs) mozna uzyc authorize wklejajac token jwt
# jwt bearer token, standard oAuth2
security = HTTPBearer()

#region funkcje sprawdzajace poziom autoryzacji 

# zezwoli na dostep tylko zalogowanemu userowi dowolnej roli
async def get_current_user(
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: SessionDep
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nieprawidłowe dane uwierzytelniające (Token nieważny)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # HTTPBearer zwraca obiekt, sam token jest w .credentials
        token_str = token.credentials 
        
        # decode JWT
        payload = jwt.decode(
            token_str, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        
        # wyciagnij ID
        user_id: str | None = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception

    # get user z bazy
    user = db.get(User, int(user_id))
    
    if user is None:
        raise credentials_exception
        
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]


# zezwala na dostep tylko adminowi
async def get_current_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Brak uprawnień. Ta akcja wymaga roli Starosty."
        )
    return user

# zezwoli na dostep tylko studentowi(useless, bo starosta tez jest studentem wiem :v)
async def get_current_student(user: CurrentUser) -> User:
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=403,
            detail="Ta akcja jest dostępna tylko dla Studentów."
        )
    return user

# skróty typów
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
CurrentStudent = Annotated[User, Depends(get_current_student)]

#endregion