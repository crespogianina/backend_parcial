from datetime import datetime, timedelta, timezone
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") #bcrypt 12 rondas


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"type": "access", "exp": expire })

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token_con_motivo(token: str) -> tuple[dict | None, str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        if payload.get("type") != "access":
            return None, "invalido"

        return payload, "ok"

    except ExpiredSignatureError:
        return None, "expirado"
    except JWTError:
        return None, "invalido"
    

def decode_access_token(token: str) -> dict | None:
    payload, _ = decode_token_con_motivo(token)
    return payload