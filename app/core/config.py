from functools import lru_cache
from secrets import token_urlsafe
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MedStock Insight API"
    environment: str = "development"
    debug: bool = False

    database_url: str = "postgresql+psycopg://localhost:5432/medstock"

    jwt_secret_key: str = Field(default_factory=lambda: token_urlsafe(48), min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @model_validator(mode="after")
    def validate_security(self):
        if self.jwt_algorithm != "HS256":
            raise ValueError("Only the configured HS256 signing algorithm is supported")
        if self.access_token_expire_minutes <= 0:
            raise ValueError("Token lifetime must be positive")
        if self.jwt_secret_key.startswith(("replace-", "dev-only-")):
            raise ValueError("JWT_SECRET_KEY must be a generated random secret")
        for origin in self.cors_origin_list:
            parsed = urlparse(origin)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                    or parsed.username or parsed.password or parsed.path not in {"", "/"}
                    or parsed.query or parsed.fragment or "*" in origin):
                raise ValueError("CORS origins must be explicit HTTP(S) origins")
        if self.environment not in {"development", "test", "demonstration"}:
            if self.debug:
                raise ValueError("Debug must be disabled outside local demonstration/test")
            if "jwt_secret_key" not in self.model_fields_set:
                raise ValueError("A persistent JWT_SECRET_KEY is required outside local demonstration/test")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
