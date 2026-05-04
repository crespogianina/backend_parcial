from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import create_access_token
from app.core.passwords import verify_password
from app.modules.auth.schemas import Token, LoginData
from app.modules.usuario.service import UsuarioService

router = APIRouter(prefix="/auth", tags=["Autenticación"]) 


@router.post("/login", response_model=Token)
async def login(data: LoginData, session: Session = Depends(get_session)):
    svc = UsuarioService(session)
    user = svc.get_by_email(data.email)

    if not user and not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.email)

    return {"access_token": access_token, "token_type": "bearer", "user": { "id": user.id, "email": user.email, "rol" : user.rol},
}