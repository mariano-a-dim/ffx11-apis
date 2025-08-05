import os
import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.logging import get_logger

# Debug: Imprimir variables de entorno
print("=== ENVIRONMENT VARIABLES ===")
for key, value in os.environ.items():
    if any(keyword in key.upper() for keyword in ['PROJECT', 'POSTGRES', 'FIRST', 'RAILWAY']):
        print(f"{key}: {value}")
print("============================")

# Inicializar logger
logger = get_logger(__name__)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)
    logger.info("Sentry initialized", environment=settings.ENVIRONMENT)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

logger.info("FastAPI application created", title=settings.PROJECT_NAME)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware added", origins=settings.all_cors_origins)

app.include_router(api_router, prefix=settings.API_V1_STR)
logger.info("API router included", prefix=settings.API_V1_STR)
