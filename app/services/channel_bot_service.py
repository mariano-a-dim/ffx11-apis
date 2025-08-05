from sqlmodel import Session
import httpx
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai_service import AIService
from app.models.channel_specialist import ChannelSpecialist, ChannelSpecialistCreate
# Guardar el mensaje en la base de datos
from app.crud.slack_message import create_slack_message
from app.models.slack import SlackMessageCreate

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
            message_id = event.get("client_msg_id") or timestamp
            
            # Ignorar mensajes del propio bot
            if event.get("bot_id"):
                return
            
            # Ignorar mensajes de subclases (ediciones, eliminaciones, etc.)
            if event.get("subtype"):
                return
            
            # Verificar si ya respondimos a este mensaje
            if await self._has_already_responded(channel_id, message_id):
                logger.info("Already responded to this message", 
                           channel_id=channel_id,
                           message_id=message_id)
                return
            
            logger.info("Processing channel message", 
                       channel_id=channel_id,
                       user_id=user_id,
                       text_length=len(text))

            slack_message = SlackMessageCreate(
                slack_message_id=event.get("client_msg_id") or event.get("ts"),
                team_id=event.get("team") or "unknown",
                channel_id=event.get("channel"),
                channel_name=None,
                user_id=event.get("user"),
                user_name=None,
                text=event.get("text", ""),
                message_type=event.get("type", "message"),
                subtype=event.get("subtype"),
                timestamp=event.get("ts"),
                thread_ts=event.get("thread_ts"),
                parent_user_id=event.get("parent_user_id"),
                client_msg_id=event.get("client_msg_id"),
                is_bot=bool(event.get("bot_id")),
                files=event.get("files", []),
                blocks=event.get("blocks", []),
                reactions=event.get("reactions", []),
                edited=event.get("edited"),
                reply_count=event.get("reply_count"),
                reply_users_count=event.get("reply_users_count"),
                latest_reply=event.get("latest_reply"),
                subscribed=event.get("subscribed"),
                raw_event=event
            )
            create_slack_message(session=self.session, slack_message_in=slack_message)
                    
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
            message_id = event.get("client_msg_id") or event.get("ts")
            
            logger.info("Processing app mention", 
                       channel_id=channel_id,
                       user_id=user_id,
                       text=text)
            
            # Verificar si ya respondimos a este mensaje
            if await self._has_already_responded(channel_id, message_id):
                logger.info("Already responded to this mention", 
                           channel_id=channel_id,
                           message_id=message_id)
                return
            
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
            
            # Seleccionar el especialista más relevante automáticamente
            relevant_specialist = await self.select_relevant_specialist(cleaned_text, specialists)
            if not relevant_specialist:
                # Si no encuentra especialista relevante, usar el primero
                relevant_specialist = specialists[0]
            
            # Generar respuesta del especialista seleccionado
            response = await self.generate_specialist_response(
                cleaned_text, relevant_specialist, channel_id, user_id
            )
            
            if response:
                await self.send_channel_message(channel_id, response, relevant_specialist.name)
                # Marcar que ya respondimos a este mensaje
                await self._mark_as_responded(channel_id, message_id)
            
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
            response = self.ai_service.generate_response(analysis_prompt)
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
        Genera una respuesta usando el especialista seleccionado con memoria del canal.
        """
        try:
            logger.info("Starting specialist response generation", 
                       channel_id=channel_id,
                       specialist=specialist.name,
                       text_length=len(text))
            
            # Obtener memoria del canal
            memory_context = self.ai_service.get_or_create_channel_memory(channel_id, limit=5)
            memory = memory_context.get("memory")
            
            logger.info("Retrieved memory context", 
                       channel_id=channel_id,
                       has_memory=bool(memory),
                       memory_size=len(memory.chat_memory.messages) if memory else 0)
            
            # Crear prompt contextual con memoria
            memory_text = ""
            if memory and memory.chat_memory.messages:
                memory_text = "\n\nContexto de la conversación reciente:\n"
                for msg in memory.chat_memory.messages[-3:]:  # Últimos 3 mensajes
                    if hasattr(msg, 'content'):
                        memory_text += f"- {msg.content}\n"
            
            # Crear prompt contextual
            prompt = f"""
            {specialist.system_prompt}
            
            Contexto: Eres {specialist.name} en un canal de Slack. Responde de manera natural y directa, como lo haría un humano en una conversación casual.
            
            Reglas importantes:
            - NO uses saludos como "¡Hola!" o "Hola"
            - Responde directamente a la pregunta o comentario
            - Sé natural y conversacional
            - No parezcas un bot o asistente
            - Considera el contexto de la conversación reciente
            - NO repitas información que ya se mencionó en el contexto
            {memory_text}
            
            Mensaje del usuario: "{text}"
            
            Responde como {specialist.name}:
            """
            
            logger.info("Generated prompt", 
                       channel_id=channel_id,
                       prompt_length=len(prompt))
            
            response = self.ai_service.generate_response(prompt)
            
            logger.info("Generated response", 
                       channel_id=channel_id,
                       response_length=len(response) if response else 0)
            
            # Actualizar memoria con el nuevo mensaje y respuesta
            if memory and response:
                memory.chat_memory.add_user_message(text)
                memory.chat_memory.add_ai_message(response)
                logger.info("Updated memory", 
                           channel_id=channel_id,
                           new_memory_size=len(memory.chat_memory.messages))
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating specialist response: {e}", 
                        channel_id=channel_id,
                        specialist=specialist.name,
                        error=str(e))
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
                        "text": text,
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
    
    def _format_specialists_for_analysis(self, specialists: List[ChannelSpecialist]) -> str:
        """
        Formatea los especialistas para el análisis de AI.
        """
        formatted = ""
        for specialist in specialists:
            keywords = ", ".join(specialist.expertise_keywords)
            formatted += f"- {specialist.name}: {specialist.description} (keywords: {keywords})\n"
        return formatted
    
    async def _has_already_responded(self, channel_id: str, message_id: str) -> bool:
        """
        Verifica si ya respondimos a este mensaje específico.
        """
        try:
            # TODO: Implementar verificación en base de datos
            # Por ahora, usar un cache simple en memoria
            cache_key = f"{channel_id}:{message_id}"
            
            # Verificar si ya procesamos este mensaje
            if hasattr(self, '_processed_messages'):
                if cache_key in self._processed_messages:
                    return True
            else:
                self._processed_messages = set()
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if already responded: {e}")
            return False
    
    async def _mark_as_responded(self, channel_id: str, message_id: str) -> None:
        """
        Marca que ya respondimos a este mensaje.
        """
        try:
            cache_key = f"{channel_id}:{message_id}"
            
            if not hasattr(self, '_processed_messages'):
                self._processed_messages = set()
            
            self._processed_messages.add(cache_key)
            
            # Limpiar cache antiguo (mantener solo últimos 100 mensajes)
            if len(self._processed_messages) > 100:
                # Convertir a lista y tomar los últimos 100
                messages_list = list(self._processed_messages)
                self._processed_messages = set(messages_list[-100:])
            
            logger.info("Marked message as responded", 
                       channel_id=channel_id,
                       message_id=message_id)
            
        except Exception as e:
            logger.error(f"Error marking message as responded: {e}")
    
    async def handle_request(self, request: Dict[str, Any]) -> None:
        """
        Maneja una solicitud entrante de Slack.
        """
        try:
            logger.info("Received request", request=request)
            
            # Verificar tipo de evento
            event_type = request.get("event", {}).get("type")
            
            if event_type == "message":
                await self.handle_channel_message(request["event"])
            elif event_type == "app_mention":
                await self.handle_app_mention(request["event"])
            else:
                logger.info("Unhandled event type", event_type=event_type)
        
        except Exception as e:
            logger.error(f"Error handling request: {e}")
    
    async def retry_handler(self, request: Dict[str, Any]) -> None:
        """
        Maneja reintentos de entrega de Slack.
        """
        try:
            logger.info("Received retry request", request=request)
            
            # Obtener número de reintento
            retry_num = request.headers.get("X-Slack-Retry-Num")
            if retry_num is not None and int(retry_num) > 1:
                logger.info("Slack retry detected, skipping processing", retry_num=retry_num)
                return
            
            # Procesar normalmente
            await self.handle_request(request)
        
        except Exception as e:
            logger.error(f"Error in retry handler: {e}")