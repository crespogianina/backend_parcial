from sqlmodel import SQLModel, Field
from pydantic import EmailStr


class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"

    id:              int | None = Field(default=None, primary_key=True)
    username:        str        = Field(index=True, unique=True)
    full_name:       str
    email:           str        = Field(index=True, unique=True)  
    hashed_password: str
    role:            str        = Field(default="user")     
    disabled:        bool       = Field(default=False)
