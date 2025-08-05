from typing import Any
from sqlmodel import Session, select

from app.core.exceptions import DatabaseException, ValidationException
from app.core.logging import get_logger
from app.models import SlackMessage, SlackMessageCreate, SlackMessageUpdate

# Inicializar logger
logger = get_logger(__name__)


def create_slack_message(*, session: Session, slack_message_in: SlackMessageCreate) -> SlackMessage:
    try:
        logger.debug("Creating Slack message", slack_message_id=slack_message_in.slack_message_id)
        db_message = SlackMessage.model_validate(slack_message_in)
        session.add(db_message)
        session.commit()
        session.refresh(db_message)
        logger.info("Slack message created successfully", slack_message_id=db_message.slack_message_id)
        return db_message
    except Exception as e:
        session.rollback()
        logger.error("Failed to create Slack message", error=str(e), slack_message_id=slack_message_in.slack_message_id)
        raise DatabaseException(f"Failed to create Slack message: {str(e)}")


def get_slack_message_by_id(*, session: Session, slack_message_id: str) -> SlackMessage | None:
    logger.debug("Getting Slack message by ID", slack_message_id=slack_message_id)
    statement = select(SlackMessage).where(SlackMessage.slack_message_id == slack_message_id)
    message = session.exec(statement).first()
    if message:
        logger.debug("Slack message found", slack_message_id=slack_message_id)
    else:
        logger.debug("Slack message not found", slack_message_id=slack_message_id)
    return message


def get_slack_messages(
    *, 
    session: Session, 
    skip: int = 0, 
    limit: int = 100,
    team_id: str | None = None,
    channel_id: str | None = None,
    user_id: str | None = None
) -> list[SlackMessage]:
    # Validaciones de entrada
    if skip < 0:
        raise ValidationException("skip must be >= 0")
    if limit <= 0 or limit > 1000:
        raise ValidationException("limit must be between 1 and 1000")
    
    logger.debug("Getting Slack messages", skip=skip, limit=limit, team_id=team_id, channel_id=channel_id, user_id=user_id)
    
    statement = select(SlackMessage)
    
    if team_id:
        statement = statement.where(SlackMessage.team_id == team_id)
    
    if channel_id:
        statement = statement.where(SlackMessage.channel_id == channel_id)
    
    if user_id:
        statement = statement.where(SlackMessage.user_id == user_id)
    
    statement = statement.offset(skip).limit(limit).order_by(SlackMessage.timestamp.desc())
    messages = session.exec(statement).all()
    logger.info("Retrieved Slack messages", count=len(messages))
    return messages


def update_slack_message(*, session: Session, db_message: SlackMessage, message_in: SlackMessageUpdate) -> SlackMessage:
    try:
        logger.debug("Updating Slack message", slack_message_id=db_message.slack_message_id)
        message_data = message_in.model_dump(exclude_unset=True)
        db_message.sqlmodel_update(message_data)
        session.add(db_message)
        session.commit()
        session.refresh(db_message)
        logger.info("Slack message updated successfully", slack_message_id=db_message.slack_message_id)
        return db_message
    except Exception as e:
        session.rollback()
        logger.error("Failed to update Slack message", error=str(e), slack_message_id=db_message.slack_message_id)
        raise DatabaseException(f"Failed to update Slack message: {str(e)}")


def delete_slack_message(*, session: Session, slack_message_id: str) -> bool:
    try:
        logger.debug("Deleting Slack message", slack_message_id=slack_message_id)
        message = get_slack_message_by_id(session=session, slack_message_id=slack_message_id)
        if not message:
            logger.warning("Slack message not found for deletion", slack_message_id=slack_message_id)
            return False
        session.delete(message)
        session.commit()
        logger.info("Slack message deleted successfully", slack_message_id=slack_message_id)
        return True
    except Exception as e:
        session.rollback()
        logger.error("Failed to delete Slack message", error=str(e), slack_message_id=slack_message_id)
        raise DatabaseException(f"Failed to delete Slack message: {str(e)}")


def count_slack_messages(
    *, 
    session: Session,
    team_id: str | None = None,
    channel_id: str | None = None,
    user_id: str | None = None
) -> int:
    """
    Cuenta mensajes de Slack con filtros opcionales.
    Útil para paginación.
    """
    from sqlalchemy import func
    
    logger.debug("Counting Slack messages", team_id=team_id, channel_id=channel_id, user_id=user_id)
    
    statement = select(func.count(SlackMessage.id))
    
    if team_id:
        statement = statement.where(SlackMessage.team_id == team_id)
    
    if channel_id:
        statement = statement.where(SlackMessage.channel_id == channel_id)
    
    if user_id:
        statement = statement.where(SlackMessage.user_id == user_id)
    
    count = session.exec(statement).first() or 0
    logger.debug("Slack messages count", count=count)
    return count 