import os
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

    @model_validator(mode="before")
    @classmethod
    def validate_railway_environment(cls, values):
        """Ensure RAILWAY_ENVIRONMENT is treated as string"""
        print(f"🔍 [DEBUG] validate_railway_environment called with values type: {type(values)}")
        
        if isinstance(values, dict):
            print(f"🔍 [DEBUG] Values keys: {list(values.keys())}")
            
            if "RAILWAY_ENVIRONMENT" in values:
                railway_env = values["RAILWAY_ENVIRONMENT"]
                print(f"🔍 [DEBUG] RAILWAY_ENVIRONMENT found: {railway_env} (type: {type(railway_env)})")
                
                if railway_env is not None:
                    original_value = railway_env
                    values["RAILWAY_ENVIRONMENT"] = str(railway_env)
                    print(f"🔍 [DEBUG] Converted RAILWAY_ENVIRONMENT from {original_value} ({type(original_value)}) to {values['RAILWAY_ENVIRONMENT']} ({type(values['RAILWAY_ENVIRONMENT'])})")
                else:
                    print(f"🔍 [DEBUG] RAILWAY_ENVIRONMENT is None, keeping as None")
            else:
                print(f"🔍 [DEBUG] RAILWAY_ENVIRONMENT not found in values")
        else:
            print(f"🔍 [DEBUG] Values is not a dict, it's: {type(values)}")
            
        return values

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_railway_environment(self) -> bool:
        """Check if running in Railway environment"""
        return self.RAILWAY_ENVIRONMENT is not None and self.RAILWAY_ENVIRONMENT != ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def railway_environment_name(self) -> str | None:
        """Get the Railway environment name (e.g., 'production')"""
        return self.RAILWAY_ENVIRONMENT

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
    DATABASE_URL: PostgresDsn

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """
        Returns the database URL with the modern psycopg dialect.
        Converts postgresql:// to postgresql+psycopg:// for compatibility with psycopg[binary].
        """
        import re
        database_url = str(self.DATABASE_URL)
        return re.sub(r'^postgresql:', 'postgresql+psycopg:', database_url)

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
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self


# Debug: Mostrar variables de entorno relacionadas con Railway
print("🔍 [DEBUG] Environment variables related to Railway:")
for key, value in os.environ.items():
    if 'RAILWAY' in key.upper():
        print(f"🔍 [DEBUG] {key}: {value} (type: {type(value)})")

print("🔍 [DEBUG] About to create Settings instance...")
try:
    settings = Settings()  # type: ignore
    print("🔍 [DEBUG] Settings instance created successfully")
    print(f"🔍 [DEBUG] RAILWAY_ENVIRONMENT value: {settings.RAILWAY_ENVIRONMENT} (type: {type(settings.RAILWAY_ENVIRONMENT)})")
except Exception as e:
    print(f"🔍 [DEBUG] Error creating Settings: {e}")
    print(f"🔍 [DEBUG] Error type: {type(e)}")
    raise
