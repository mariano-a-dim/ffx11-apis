import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use .env file in the root directory
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    
    # Railway specific configuration
    RAILWAY_ENVIRONMENT: str | None = None
    RAILWAY_STATIC_URL: str | None = None
    PORT: int = 8000

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_railway_environment(self) -> bool:
        """Check if running in Railway environment"""
        return self.RAILWAY_ENVIRONMENT is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        origins = [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]
        
        # Add frontend host
        if self.FRONTEND_HOST:
            origins.append(self.FRONTEND_HOST)
            
        # Add Railway static URL if available
        if self.RAILWAY_STATIC_URL:
            origins.append(self.RAILWAY_STATIC_URL)
            
        return origins

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: EmailStr | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str
    
    # Slack OAuth Configuration
    SLACK_CLIENT_ID: str | None = None
    SLACK_CLIENT_SECRET: str | None = None
    SLACK_SIGNING_SECRET: str | None = None
    SLACK_BOT_TOKEN: str | None = None
    SLACK_REDIRECT_URI: str | None = None
    SLACK_PERSONAL_TOKEN: str | None = None  # Token personal para obtener información de usuarios

    # OpenAI Configuration
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o"
    
    # AI Assistant Configuration
    AI_PRINCIPAL_USER_ID: str | None = None  # ID de Slack del usuario principal (Madim)
    AI_PRINCIPAL_USER_NAME: str = "Madim"  # Nombre del usuario principal
    AI_COMPANY_NAME: str = "Gojiraf"  # Nombre de la empresa
    AI_PRINCIPAL_ROLE: str = "CTO"  # Rol del usuario principal
    
    # Response Delay Configuration (in seconds)
    RESPONSE_DELAY_HIGH: int = 30      # 30 segundos para alta urgencia
    RESPONSE_DELAY_MEDIUM: int = 120   # 2 minutos para urgencia media
    RESPONSE_DELAY_LOW: int = 300      # 5 minutos para baja urgencia
    RESPONSE_DELAY_LOCO: int = 5       # 5 segundos para palabra "loco"
    RESPONSE_DELAY_TEST: int = 30      # 30 segundos para pruebas

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self


settings = Settings()  # type: ignore
