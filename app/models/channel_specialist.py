from sqlmodel import SQLModel, Field
from typing import List, Optional, Any
from datetime import datetime
from sqlalchemy import JSON, Column


class ChannelSpecialistBase(SQLModel):
    """Modelo base para especialistas del canal."""
    name: str = Field(description="Nombre del especialista")
    description: str = Field(description="Descripción del especialista")
    expertise_keywords: Any = Field(default_factory=list, sa_column=Column(JSON), description="Palabras clave de expertise")
    system_prompt: str = Field(description="Prompt del sistema para el especialista")
    is_active: bool = Field(default=True, description="Si el especialista está activo")
    channel_id: str = Field(description="ID del canal donde está configurado")


class ChannelSpecialistCreate(ChannelSpecialistBase):
    """Modelo para crear un nuevo especialista."""
    pass


class ChannelSpecialistUpdate(SQLModel):
    """Modelo para actualizar un especialista."""
    name: Optional[str] = None
    description: Optional[str] = None
    expertise_keywords: Optional[Any] = None
    system_prompt: Optional[str] = None
    is_active: Optional[bool] = None


class ChannelSpecialist(ChannelSpecialistBase, table=True):
    """Modelo completo para especialistas del canal."""
    __tablename__ = "channel_specialists"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ChannelSpecialistPublic(SQLModel):
    """Modelo público para especialistas del canal."""
    id: int
    name: str
    description: str
    expertise_keywords: Any
    is_active: bool
    channel_id: str
    created_at: datetime
    updated_at: datetime 