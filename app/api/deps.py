import uuid
from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.core.exceptions import UnauthorizedException, NotFoundException, ForbiddenException
from app.models import TokenPayload, User
from app.crud.user import get_user_by_email, get_user_by_id
from app.services.ai_service import AIService
from app.services.slack_service import SlackService

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise UnauthorizedException("Could not validate credentials")
    
    # El token contiene el ID del usuario, no el email
    try:
        user_id = uuid.UUID(token_data.sub)
        user = get_user_by_id(session=session, user_id=user_id)
    except ValueError:
        # Fallback: intentar buscar por email (para compatibilidad)
        user = get_user_by_email(session=session, email=token_data.sub)
    
    if not user:
        raise NotFoundException("User")
    if not user.is_active:
        raise UnauthorizedException("Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise ForbiddenException("The user doesn't have enough privileges")
    return current_user


# Dependencias para servicios
def get_ai_service(session: SessionDep) -> AIService:
    return AIService(session)


def get_slack_service(session: SessionDep) -> SlackService:
    return SlackService(session)
