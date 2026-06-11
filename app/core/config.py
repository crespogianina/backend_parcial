from typing import Optional

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "localhost" 
    postgres_port: int = 5432
    postgres_db: str = "foodstore_db"
    database_url_env: Optional[str] = Field(default=None, validation_alias="DATABASE_URL")

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        if self.database_url_env:
            return self.database_url_env

        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    SECRET_KEY: str 
    ALGORITHM:  str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    CORS_ORIGINS: list[str]

    MP_ACCESS_TOKEN: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("MP_ACCESS_TOKEN", "MERCADOPAGO_ACCESS_TOKEN"),
    )
    MP_PUBLIC_KEY: Optional[str] = None
    MP_NOTIFICATION_URL: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("MP_NOTIFICATION_URL", "MP_WEBHOOK_URL"),
    )
    NGROK_URL: Optional[str] = None

    # Agregadas como opcionales para no romper el backend hoy
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None

    VITE_API_URL: str = "http://localhost:8000"

    @property
    def MP_WEBHOOK_URL(self) -> Optional[str]:
        return self.MP_NOTIFICATION_URL

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()