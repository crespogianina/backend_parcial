from sqlmodel import SQLModel


class CloudinaryResponse(SQLModel):
    secure_url: str
    public_id: str
    width: int
    height: int
    format: str
    resource_type: str
