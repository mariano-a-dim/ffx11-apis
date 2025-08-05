import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlmodel import Session

from app.core.logging import LoggerMixin
from app.core.config import settings
from app.services.ai_service import AIService


class SlackResponseScheduler(LoggerMixin):
    """
    Servicio para programar respuestas de Slack basadas en la urgencia del mensaje.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.ai_service = AIService(session)
        
        # Configuración de tiempos de respuesta por urgencia (en minutos)
        self.response_times = {
            "high": {"min": 1, "max": 5},      # 1-5 minutos
            "medium": {"min": 5, "max": 10},   # 5-10 minutos  
            "low": {"min": 10, "max": 15},     # 10-15 minutos
            "none": {"min": 20, "max": 30}     # 20-30 minutos
        }
    
    def schedule_response(self, message: Dict[str, Any], urgency_level: str, 
                         response: str, team_id: str) -> None:
        """
        Programa una respuesta para ser enviada según el nivel de urgencia.
        """
        try:
            # Determinar delay según urgencia usando configuración del .env
            if urgency_level == "high":
                delay_seconds = settings.RESPONSE_DELAY_HIGH
            elif urgency_level == "medium":
                delay_seconds = settings.RESPONSE_DELAY_MEDIUM
            else:  # low
                delay_seconds = settings.RESPONSE_DELAY_LOW
            
            # Calcular tiempo de envío
            send_time = datetime.now() + timedelta(seconds=delay_seconds)
            
            self.logger.info("📅 Scheduling Slack response", 
                           urgency_level=urgency_level,
                           delay_seconds=delay_seconds,
                           send_time=send_time.strftime("%H:%M:%S"),
                           channel_id=message.get("channel"),
                           message_preview=response[:100])
            
            # Programar la tarea asíncrona
            task = asyncio.create_task(
                self._send_delayed_response(
                    message, response, team_id, delay_seconds
                )
            )
            
            self.logger.info("📋 Task created successfully", 
                           task_id=id(task),
                           delay_seconds=delay_seconds)
            
        except Exception as e:
            self.logger.error("Error scheduling response", 
                            error=str(e), 
                            urgency_level=urgency_level)
    
    def schedule_test_response(self, message: Dict[str, Any], response: str, 
                             team_id: str, delay_seconds: int = None) -> None:
        """
        Programa una respuesta de prueba con delay personalizado.
        """
        try:
            # Usar configuración del .env si no se especifica delay
            if delay_seconds is None:
                delay_seconds = settings.RESPONSE_DELAY_TEST
            
            # Calcular tiempo de envío
            send_time = datetime.now() + timedelta(seconds=delay_seconds)
            
            self.logger.info("🧪 Scheduling test response", 
                           delay_seconds=delay_seconds,
                           send_time=send_time.strftime("%H:%M:%S"),
                           channel_id=message.get("channel"),
                           message_preview=response[:100])
            
            # Programar la tarea asíncrona
            task = asyncio.create_task(
                self._send_delayed_response(
                    message, response, team_id, delay_seconds
                )
            )
            
            self.logger.info("🧪 Test task created successfully", 
                           task_id=id(task),
                           delay_seconds=delay_seconds)
            
        except Exception as e:
            self.logger.error("Error scheduling test response", 
                            error=str(e))
    
    def schedule_loco_response(self, message: Dict[str, Any], response: str, 
                             team_id: str) -> None:
        """
        Programa una respuesta específica para mensajes con "loco".
        """
        try:
            delay_seconds = settings.RESPONSE_DELAY_LOCO  # Delay configurado para "loco"
            
            # Calcular tiempo de envío
            send_time = datetime.now() + timedelta(seconds=delay_seconds)
            
            self.logger.info("🎯 Scheduling 'loco' response", 
                           delay_seconds=delay_seconds,
                           send_time=send_time.strftime("%H:%M:%S"),
                           channel_id=message.get("channel"),
                           message_preview=response[:100])
            
            # Programar la tarea asíncrona
            task = asyncio.create_task(
                self._send_delayed_response(
                    message, response, team_id, delay_seconds
                )
            )
            
            self.logger.info("🎯 'Loco' task created successfully", 
                           task_id=id(task),
                           delay_seconds=delay_seconds)
            
        except Exception as e:
            self.logger.error("Error scheduling 'loco' response", 
                            error=str(e))
    
    async def _send_delayed_response(self, message: Dict[str, Any], 
                                   response: str, team_id: str, 
                                   delay_seconds: int) -> None:
        """
        Envía la respuesta después del delay programado.
        """
        try:
            self.logger.info("⏰ Starting delayed response task", 
                           delay_seconds=delay_seconds,
                           channel_id=message.get("channel"))
            
            # Esperar el tiempo programado
            self.logger.info("😴 Sleeping for delay", delay_seconds=delay_seconds)
            await asyncio.sleep(delay_seconds)
            self.logger.info("✅ Delay completed, sending response")
            
            # Enviar la respuesta
            success = await self._send_slack_response(
                message.get("channel"),
                response,
                message.get("thread_ts"),
                team_id
            )
            
            if success:
                self.logger.info("✅ Delayed response sent successfully", 
                               channel_id=message.get("channel"),
                               delay_seconds=delay_seconds)
            else:
                self.logger.error("❌ Failed to send delayed response", 
                                channel_id=message.get("channel"))
                
        except Exception as e:
            self.logger.error("Error in delayed response", 
                            error=str(e),
                            channel_id=message.get("channel"))
    
    async def _send_slack_response(self, channel_id: str, response: str, 
                                 thread_ts: Optional[str], team_id: str) -> bool:
        """
        Envía la respuesta a Slack usando la API.
        """
        try:
            import httpx
            from app.core.config import settings
            
            # Usar el token personal para enviar mensajes
            access_token = settings.SLACK_PERSONAL_TOKEN
            if not access_token:
                self.logger.error("No Slack token configured for sending messages")
                return False
            
            # Preparar datos para la API de Slack
            data = {
                "channel": channel_id,
                "text": response
            }
            
            # Si hay thread_ts, responder en el thread
            if thread_ts:
                data["thread_ts"] = thread_ts
            
            self.logger.info("📤 Sending response to Slack", 
                           channel_id=channel_id,
                           thread_ts=thread_ts,
                           response_length=len(response),
                           response_preview=response[:100])
            
            # Enviar mensaje usando la API de Slack
            async with httpx.AsyncClient() as client:
                response_api = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=data
                )
                
                if response_api.status_code == 200:
                    result = response_api.json()
                    if result.get("ok"):
                        self.logger.info("✅ Message sent successfully to Slack", 
                                       channel_id=channel_id,
                                       ts=result.get("ts"))
                        return True
                    else:
                        self.logger.error("❌ Slack API error", 
                                        error=result.get("error"),
                                        channel_id=channel_id)
                        return False
                else:
                    self.logger.error("❌ HTTP error sending to Slack", 
                                    status_code=response_api.status_code,
                                    channel_id=channel_id)
                    return False
            
        except Exception as e:
            self.logger.error("Error sending Slack response", 
                            error=str(e),
                            channel_id=channel_id,
                            exc_info=True)
            return False
    
    def get_urgency_response_time(self, urgency_level: str) -> Dict[str, Any]:
        """
        Obtiene información sobre el tiempo de respuesta para una urgencia.
        """
        time_range = self.response_times.get(urgency_level, self.response_times["none"])
        return {
            "urgency_level": urgency_level,
            "min_minutes": time_range["min"],
            "max_minutes": time_range["max"],
            "description": self._get_urgency_description(urgency_level)
        }
    
    def _get_urgency_description(self, urgency_level: str) -> str:
        """Obtiene descripción de la urgencia."""
        descriptions = {
            "high": "Respuesta inmediata (1-5 minutos)",
            "medium": "Respuesta rápida (5-10 minutos)", 
            "low": "Respuesta normal (10-15 minutos)",
            "none": "Respuesta cuando sea posible (20-30 minutos)"
        }
        return descriptions.get(urgency_level, "Tiempo no definido") 