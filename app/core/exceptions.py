from fastapi import HTTPException
from typing import Any, Dict, Optional


class AppException(HTTPException):
    """Excepción base personalizada para la aplicación."""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class DatabaseException(AppException):
    """Excepción para errores de base de datos."""
    
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(status_code=500, detail=detail)


class ValidationException(AppException):
    """Excepción para errores de validación."""
    
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=400, detail=detail)


class NotFoundException(AppException):
    """Excepción para recursos no encontrados."""
    
    def __init__(self, resource: str = "Resource"):
        super().__init__(status_code=404, detail=f"{resource} not found")


class UnauthorizedException(AppException):
    """Excepción para acceso no autorizado."""
    
    def __init__(self, detail: str = "Not authorized"):
        super().__init__(status_code=401, detail=detail)


class ForbiddenException(AppException):
    """Excepción para acceso prohibido."""
    
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(status_code=403, detail=detail)


class ConflictException(AppException):
    """Excepción para conflictos de datos."""
    
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(status_code=409, detail=detail)


class SlackException(AppException):
    """Excepción para errores de Slack."""
    
    def __init__(self, detail: str = "Slack operation failed"):
        super().__init__(status_code=500, detail=detail)


class AIServiceException(AppException):
    """Excepción para errores del servicio de IA."""
    
    def __init__(self, detail: str = "AI service error"):
        super().__init__(status_code=500, detail=detail) 