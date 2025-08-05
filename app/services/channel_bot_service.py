from sqlmodel import Session
import httpx
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai_service import AIService
from app.models.channel_specialist import ChannelSpecialist, ChannelSpecialistCreate

logger = get_logger(__name__)


class ChannelBotService:
    """
    Servicio para manejar el bot público del canal con especialistas.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.ai_service = AIService(session=session)
        self.slack_api_url = "https://slack.com/api"
        self.bot_token = settings.SLACK_BOT_TOKEN
    
    async def handle_channel_message(self, event: Dict[str, Any]) -> None:
        """
        Maneja mensajes regulares en el canal.
        Analiza el contexto y decide si algún especialista debe responder.
        """
        try:
            channel_id = event.get("channel")
            user_id = event.get("user")
            text = event.get("text", "")
            timestamp = event.get("ts")
            
            # Ignorar mensajes del propio bot
            if event.get("bot_id"):
                return
            
            # Ignorar mensajes de subclases (ediciones, eliminaciones, etc.)
            if event.get("subtype"):
                return
            
            logger.info("Processing channel message", 
                       channel_id=channel_id,
                       user_id=user_id,
                       text_length=len(text))
            
            # Obtener especialistas configurados para este canal
            specialists = await self.get_channel_specialists(channel_id)
            if not specialists:
                logger.info("No specialists configured for channel", channel_id=channel_id)
                return
            
            # Analizar el mensaje para determinar qué especialista debe responder
            relevant_specialist = await self.select_relevant_specialist(text, specialists)
            if not relevant_specialist:
                logger.info("No relevant specialist found for message", channel_id=channel_id)
                return
            
            # Generar respuesta del especialista
            response = await self.generate_specialist_response(
                text, relevant_specialist, channel_id, user_id
            )
            
            if response:
                await self.send_channel_message(channel_id, response, relevant_specialist.name)
            
        except Exception as e:
            logger.error(f"Error handling channel message: {e}")
    
    async def handle_app_mention(self, event: Dict[str, Any]) -> None:
        """
        Maneja cuando alguien menciona al bot directamente.
        """
        try:
            channel_id = event.get("channel")
            user_id = event.get("user")
            text = event.get("text", "")
            
            logger.info("Processing app mention", 
                       channel_id=channel_id,
                       user_id=user_id,
                       text=text)
            
            # Remover la mención del bot del texto
            cleaned_text = self._remove_bot_mention(text)
            
            # Obtener especialistas del canal
            specialists = await self.get_channel_specialists(channel_id)
            if not specialists:
                await self.send_channel_message(
                    channel_id, 
                    "No tengo especialistas configurados para este canal. Contacta al administrador.",
                    "Bot"
                )
                return
            
            # Si hay múltiples especialistas, preguntar cuál usar
            if len(specialists) > 1:
                response = self._create_specialist_selection_message(specialists, cleaned_text)
                await self.send_channel_message(channel_id, response, "Bot")
                return
            
            # Si hay solo un especialista, usarlo directamente
            specialist = specialists[0]
            response = await self.generate_specialist_response(
                cleaned_text, specialist, channel_id, user_id
            )
            
            if response:
                await self.send_channel_message(channel_id, response, specialist.name)
            
        except Exception as e:
            logger.error(f"Error handling app mention: {e}")
    
    async def get_channel_specialists(self, channel_id: str) -> List[ChannelSpecialist]:
        """
        Obtiene los especialistas configurados para un canal específico.
        """
        # TODO: Implementar consulta a la base de datos
        # Por ahora, retornar especialistas de prueba
        return [
            ChannelSpecialist(
                id=1,
                name="Arquitecto de Software",
                description="Especialista en arquitectura y diseño de software",
                expertise_keywords=["arquitectura", "diseño", "patrones", "microservicios", "escalabilidad"],
                system_prompt="Eres un arquitecto de software experimentado. Proporciona consejos sobre diseño, patrones arquitectónicos, y mejores prácticas.",
                is_active=True,
                channel_id=channel_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            ChannelSpecialist(
                id=2,
                name="Desarrollador Node.js",
                description="Especialista en desarrollo con Node.js y JavaScript",
                expertise_keywords=["nodejs", "javascript", "npm", "express", "async", "promises"],
                system_prompt="Eres un desarrollador experto en Node.js. Ayuda con problemas de JavaScript, npm, y desarrollo backend.",
                is_active=True,
                channel_id=channel_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
    
    async def select_relevant_specialist(self, text: str, specialists: List[ChannelSpecialist]) -> Optional[ChannelSpecialist]:
        """
        Selecciona el especialista más relevante basado en el contenido del mensaje.
        """
        try:
            # Crear prompt para analizar el texto
            analysis_prompt = f"""
            Analiza el siguiente mensaje y determina qué especialista es más relevante.
            
            Mensaje: "{text}"
            
            Especialistas disponibles:
            {self._format_specialists_for_analysis(specialists)}
            
            Responde solo con el nombre del especialista más relevante, o "ninguno" si no hay ninguno relevante.
            """
            
            # Usar AI para analizar
            response = await self.ai_service.generate_response(analysis_prompt)
            selected_name = response.strip().lower()
            
            # Encontrar el especialista seleccionado
            for specialist in specialists:
                if specialist.name.lower() in selected_name:
                    logger.info(f"Selected specialist: {specialist.name}")
                    return specialist
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting specialist: {e}")
            return None
    
    async def generate_specialist_response(self, text: str, specialist: ChannelSpecialist, channel_id: str, user_id: str) -> Optional[str]:
        """
        Genera una respuesta usando el especialista seleccionado.
        """
        try:
            # Crear prompt contextual
            prompt = f"""
            {specialist.system_prompt}
            
            Contexto: Eres {specialist.name} en un canal de Slack. Responde de manera útil y concisa.
            
            Mensaje del usuario: "{text}"
            
            Responde como {specialist.name}:
            """
            
            response = await self.ai_service.generate_response(prompt)
            return response
            
        except Exception as e:
            logger.error(f"Error generating specialist response: {e}")
            return None
    
    async def send_channel_message(self, channel_id: str, text: str, specialist_name: str) -> bool:
        """
        Envía un mensaje al canal de Slack.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.slack_api_url}/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {self.bot_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "channel": channel_id,
                        "text": f"*{specialist_name}:* {text}",
                        "username": specialist_name,
                        "icon_emoji": ":robot_face:"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info("Message sent successfully", channel_id=channel_id)
                        return True
                    else:
                        logger.error("Slack API error", error=result.get("error"))
                        return False
                else:
                    logger.error("HTTP error sending message", status_code=response.status_code)
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending channel message: {e}")
            return False
    
    async def configure_channel(self, channel_id: str, specialists_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Configura especialistas para un canal específico.
        """
        try:
            # TODO: Implementar guardado en base de datos
            logger.info("Configuring channel specialists", 
                       channel_id=channel_id,
                       config=specialists_config)
            
            return {
                "channel_id": channel_id,
                "specialists_count": len(specialists_config),
                "status": "configured"
            }
            
        except Exception as e:
            logger.error(f"Error configuring channel: {e}")
            raise
    
    def _remove_bot_mention(self, text: str) -> str:
        """
        Remueve la mención del bot del texto.
        """
        # Remover patrones como <@BOT_ID> o @bot_name
        import re
        return re.sub(r'<@[A-Z0-9]+>', '', text).strip()
    
    def _create_specialist_selection_message(self, specialists: List[ChannelSpecialist], text: str) -> str:
        """
        Crea un mensaje para que el usuario seleccione un especialista.
        """
        message = f"Veo que preguntaste sobre: \"{text}\"\n\n"
        message += "Tengo varios especialistas que pueden ayudarte:\n\n"
        
        for i, specialist in enumerate(specialists, 1):
            message += f"{i}. *{specialist.name}*: {specialist.description}\n"
        
        message += "\nMenciona al bot con el número del especialista que prefieres."
        
        return message
    
    def _format_specialists_for_analysis(self, specialists: List[ChannelSpecialist]) -> str:
        """
        Formatea los especialistas para el análisis de AI.
        """
        formatted = ""
        for specialist in specialists:
            keywords = ", ".join(specialist.expertise_keywords)
            formatted += f"- {specialist.name}: {specialist.description} (keywords: {keywords})\n"
        return formatted 