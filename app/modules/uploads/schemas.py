from typing import Optional

from sqlmodel import Field, SQLModel


class CloudinaryResponse(SQLModel):
    secure_url: str
    public_id: str
    width: int
    height: int
    format: str
    resource_type: str


class ImagenProductoUpdate(SQLModel):
    imagenes_url: list[str] = Field(min_length=0, max_length=10)


class ImagenCategoriaUpdate(SQLModel):
    imagen_url: Optional[str] = None
