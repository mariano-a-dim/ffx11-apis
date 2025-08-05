import logging
import sys
from typing import Any, Dict

import structlog
from structlog.stdlib import LoggerFactory

from app.core.config import settings


def setup_logging() -> None:
    """
    Configura logging estructurado para la aplicación.
    """
    # Configurar structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.ENVIRONMENT != "local" else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configurar logging estándar
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=get_log_level(),
    )


def get_log_level() -> int:
    """
    Obtiene el nivel de logging basado en el ambiente.
    """
    if settings.ENVIRONMENT == "local":
        return logging.INFO  # Cambiado de DEBUG a INFO para ver logs de Slack
    elif settings.ENVIRONMENT == "staging":
        return logging.INFO
    else:  # production
        return logging.WARNING


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Obtiene un logger estructurado.
    
    Args:
        name: Nombre del logger (generalmente __name__)
        
    Returns:
        Logger estructurado configurado
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """
    Mixin para agregar logging a las clases.
    """
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """
        Obtiene el logger para la clase.
        """
        return get_logger(self.__class__.__name__)


# Configurar logging al importar el módulo
setup_logging() 