
from pydantic import EmailStr, Field
from sqlmodel import SQLModel


class UserCreate(SQLModel):
    username:  str
    full_name: str
    email:     EmailStr
    password:  str = Field(min_length=8)


class UserPublic(SQLModel):
    id:        int
    username:  str
    full_name: str
    email:     str
    role:      str
    disabled:  bool


class Token(SQLModel):
    access_token: str
    token_type:   str = "bearer"
    expires_in:   int 
