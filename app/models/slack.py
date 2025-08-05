import uuid
from datetime import datetime, timezone
from typing import Any
from sqlmodel import Field, SQLModel
from sqlalchemy import JSON, Column


class SlackMessageBase(SQLModel):
    slack_message_id: str = Field(unique=True, index=True, max_length=255)
    team_id: str = Field(max_length=255)  # ID del workspace
    channel_id: str = Field(max_length=255)
    channel_name: str | None = Field(default=None, max_length=255)
    user_id: str = Field(max_length=255)
    user_name: str | None = Field(default=None, max_length=255)
    text: str = Field(max_length=4000)  # Slack permite hasta 4000 caracteres
    message_type: str = Field(max_length=50)  # message, file_share, etc.
    subtype: str | None = Field(default=None, max_length=50)
    timestamp: str = Field(max_length=50)
    thread_ts: str | None = Field(default=None, max_length=50)
    parent_user_id: str | None = Field(default=None, max_length=255)
    client_msg_id: str | None = Field(default=None, max_length=255)
    is_bot: bool = Field(default=False)
    files: Any = Field(default_factory=list, sa_column=Column(JSON))  # Archivos adjuntos
    blocks: Any = Field(default_factory=list, sa_column=Column(JSON))  # Bloques de contenido
    reactions: Any = Field(default_factory=list, sa_column=Column(JSON))  # Reacciones
    edited: Any = Field(default=None, sa_column=Column(JSON))  # Información de edición
    reply_count: int | None = Field(default=None)
    reply_users_count: int | None = Field(default=None)
    latest_reply: str | None = Field(default=None, max_length=50)
    subscribed: bool | None = Field(default=None)
    raw_event: Any = Field(default_factory=dict, sa_column=Column(JSON))  # Evento completo de Slack


class SlackMessageCreate(SlackMessageBase):
    pass


class SlackMessageUpdate(SQLModel):
    channel_name: str | None = Field(default=None, max_length=255)
    user_name: str | None = Field(default=None, max_length=255)
    text: str | None = Field(default=None, max_length=4000)
    raw_event: dict | None = Field(default=None)


class SlackMessage(SlackMessageBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_ai_response: bool | None = Field(default=False, nullable=True)
    

class SlackMessagePublic(SlackMessageBase):
    id: uuid.UUID
    created_at: str


class SlackMessagesPublic(SQLModel):
    data: list[SlackMessagePublic]
    count: int 