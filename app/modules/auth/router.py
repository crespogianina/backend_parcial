from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import create_access_token
from app.core.passwords import verify_password
from app.modules.auth.schemas import Token
from app.modules.usuario.service import UsuarioService

router = APIRouter(prefix="/auth", tags=["Autenticación"]) 


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    svc = UsuarioService(session)
    user = svc.get_by_email(form_data.username)

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.email)

    return {"access_token": access_token, "token_type": "bearer"}