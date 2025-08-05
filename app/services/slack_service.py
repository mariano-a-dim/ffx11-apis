from typing import Dict, Any, Optional
from sqlmodel import Session

from app.crud.slack_message import create_slack_message, get_slack_message_by_id, get_slack_messages
from app.models import SlackMessageCreate
from app.services.ai_service import AIService
from app.services.slack_response_scheduler import SlackResponseScheduler
from app.services.slack_user_service import SlackUserService
from app.core.logging import LoggerMixin


class SlackService(LoggerMixin):
    def __init__(self, session: Session):
        self.session = session
        self.ai_service = AIService(session)
        self.response_scheduler = SlackResponseScheduler(session)
        self.user_service = SlackUserService(session)

    async def process_message_event(self, event: Dict[str, Any], team_id: str, access_token: str = None) -> bool:
        """
        Procesa un evento de mensaje de Slack y lo persiste en la base de datos.
        Retorna True si se procesó correctamente, False en caso contrario.
        """
        try:
            # Log del mensaje que se está procesando
            self.logger.info("Processing Slack message", 
                           event_type=event.get("type"),
                           event_subtype=event.get("subtype"),
                           channel_id=event.get("channel"),
                           user_id=event.get("user"),
                           text=event.get("text", ""),
                           full_event=event)
            
            # Extraer datos del mensaje
            slack_message_id = event.get("client_msg_id") or event.get("ts")
            channel_id = event.get("channel", "unknown")
            user_id = event.get("user", "unknown")
            text = event.get("text", "")
            timestamp = event.get("ts", "")
            thread_ts = event.get("thread_ts")
            parent_user_id = event.get("parent_user_id")
            client_msg_id = event.get("client_msg_id")
            
            # Procesar menciones de usuario si tenemos access_token
            processed_text = text
            if access_token:
                try:
                    processed_text = await self.user_service.process_message_text(text, access_token)
                    self.logger.info("Processed user mentions", 
                                   original_text=text[:100],
                                   processed_text=processed_text[:100])
                except Exception as e:
                    self.logger.warning("Failed to process user mentions, using original text", error=str(e))
                    processed_text = text
            
            # Verificar si el mensaje ya existe para evitar duplicados
            existing_message = get_slack_message_by_id(
                session=self.session, 
                slack_message_id=slack_message_id
            )
            if existing_message:
                self.logger.info("Message already exists, skipping", 
                               slack_message_id=slack_message_id)
                return True

            # Crear objeto para persistir
            slack_message_data = SlackMessageCreate(
                slack_message_id=slack_message_id,
                team_id=team_id,
                channel_id=channel_id,
                user_id=user_id,
                text=processed_text,  # Usar texto procesado con nombres reales
                message_type=event.get("type", "message"),
                subtype=event.get("subtype"),
                timestamp=timestamp,
                thread_ts=thread_ts,
                parent_user_id=parent_user_id,
                client_msg_id=client_msg_id,
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

            # Persistir el mensaje
            created_message = create_slack_message(
                session=self.session, 
                slack_message_in=slack_message_data
            )
            self.logger.info("Message persisted successfully", 
                           message_id=created_message.id,
                           slack_message_id=slack_message_id)
            
            # Obtener contexto de conversación reciente del mismo canal
            conversation_context = get_slack_messages(
                session=self.session,
                channel_id=channel_id,
                limit=5  # Últimos 5 mensajes para contexto
            )
            
            # Filtrar para excluir el mensaje actual
            conversation_context = [msg for msg in conversation_context if msg.slack_message_id != slack_message_id]
            
            # Crear una copia del evento con el texto procesado para el AI
            ai_event = event.copy()
            ai_event["text"] = processed_text  # Usar texto procesado con nombres reales
            
            # Analizar mensaje con IA y generar respuesta si es necesario
            analysis = self.ai_service.analyze_message(ai_event, conversation_context)
            self.logger.info("AI analysis completed", 
                           analysis=analysis,
                           slack_message_id=slack_message_id)
            
            # Verificar si debe responder y generar respuesta
            if self.ai_service.should_respond(analysis):
                self.logger.info("AI determined response needed", 
                               urgency=analysis.get('urgency'),
                               reasoning=analysis.get('reasoning'),
                               slack_message_id=slack_message_id)
                
                # Generar respuesta usando el flujo completo de LangGraph
                response = self.ai_service.get_response(ai_event, conversation_context)
                if response:
                    self.logger.info("Response generated successfully", 
                                   response=response,
                                   slack_message_id=slack_message_id)
                    
                    # Obtener nivel de urgencia del análisis
                    urgency_level = analysis.get('urgency', 'low')
                    
                    # Verificar si es respuesta para "loco" y usar delay específico
                    message_text = event.get('text', '').lower()
                    if "loco" in message_text:
                        # Usar delay específico de 5 segundos para "loco"
                        self.response_scheduler.schedule_loco_response(
                            message=event,
                            response=response,
                            team_id=team_id
                        )
                        
                        self.logger.info("'Loco' response scheduled for delivery (5s delay)", 
                                       slack_message_id=slack_message_id)
                    else:
                        # Programar respuesta basada en la urgencia para otros casos
                        self.response_scheduler.schedule_response(
                            message=event,
                            urgency_level=urgency_level,
                            response=response,
                            team_id=team_id
                        )
                        
                        self.logger.info("Response scheduled for delivery", 
                                       urgency_level=urgency_level,
                                       slack_message_id=slack_message_id)
                else:
                    self.logger.warning("Failed to generate response", 
                                      slack_message_id=slack_message_id)
            
            return True

        except Exception as e:
            self.logger.error("Error processing message event", 
                            error=str(e),
                            slack_message_id=slack_message_id,
                            exc_info=True)
            return False

    def process_message_event_sync(self, event: Dict[str, Any], team_id: str) -> bool:
        """
        Versión síncrona del procesamiento de mensajes (sin procesamiento de menciones).
        Mantiene compatibilidad con código existente.
        """
        try:
            # Log del mensaje que se está procesando
            self.logger.info("Processing Slack message (sync)", 
                           event_type=event.get("type"),
                           event_subtype=event.get("subtype"),
                           channel_id=event.get("channel"),
                           user_id=event.get("user"),
                           text=event.get("text", ""))
            
            # Extraer datos del mensaje
            slack_message_id = event.get("client_msg_id") or event.get("ts")
            channel_id = event.get("channel", "unknown")
            user_id = event.get("user", "unknown")
            text = event.get("text", "")
            timestamp = event.get("ts", "")
            thread_ts = event.get("thread_ts")
            parent_user_id = event.get("parent_user_id")
            client_msg_id = event.get("client_msg_id")
            
            # Verificar si el mensaje ya existe para evitar duplicados
            existing_message = get_slack_message_by_id(
                session=self.session, 
                slack_message_id=slack_message_id
            )
            if existing_message:
                self.logger.info("Message already exists, skipping", 
                               slack_message_id=slack_message_id)
                return True

            # Crear objeto para persistir (sin procesar menciones)
            slack_message_data = SlackMessageCreate(
                slack_message_id=slack_message_id,
                team_id=team_id,
                channel_id=channel_id,
                user_id=user_id,
                text=text,  # Usar texto original
                message_type=event.get("type", "message"),
                subtype=event.get("subtype"),
                timestamp=timestamp,
                thread_ts=thread_ts,
                parent_user_id=parent_user_id,
                client_msg_id=client_msg_id,
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

            # Persistir el mensaje
            created_message = create_slack_message(
                session=self.session, 
                slack_message_in=slack_message_data
            )
            self.logger.info("Message persisted successfully", 
                           message_id=created_message.id,
                           slack_message_id=slack_message_id)
            
            # Obtener contexto de conversación reciente del mismo canal
            conversation_context = get_slack_messages(
                session=self.session,
                channel_id=channel_id,
                limit=5  # Últimos 5 mensajes para contexto
            )
            
            # Filtrar para excluir el mensaje actual
            conversation_context = [msg for msg in conversation_context if msg.slack_message_id != slack_message_id]
            
            # Analizar mensaje con IA y generar respuesta si es necesario
            analysis = self.ai_service.analyze_message(event, conversation_context)
            self.logger.info("AI analysis completed", 
                           analysis=analysis,
                           slack_message_id=slack_message_id)
            
            # Verificar si debe responder y generar respuesta
            if self.ai_service.should_respond(analysis):
                self.logger.info("AI determined response needed", 
                               urgency=analysis.get('urgency'),
                               reasoning=analysis.get('reasoning'),
                               slack_message_id=slack_message_id)
                
                # Generar respuesta usando el flujo completo de LangGraph
                response = self.ai_service.get_response(event, conversation_context)
                if response:
                    self.logger.info("Response generated successfully", 
                                   response=response,
                                   slack_message_id=slack_message_id)
                    
                    # Obtener nivel de urgencia del análisis
                    urgency_level = analysis.get('urgency', 'low')
                    
                    # Programar respuesta basada en la urgencia
                    self.response_scheduler.schedule_response(
                        message=event,
                        urgency_level=urgency_level,
                        response=response,
                        team_id=team_id
                    )
                    
                    self.logger.info("Response scheduled for delivery", 
                                   urgency_level=urgency_level,
                                   slack_message_id=slack_message_id)
                else:
                    self.logger.warning("Failed to generate response", 
                                      slack_message_id=slack_message_id)
            
            return True

        except Exception as e:
            self.logger.error("Error processing message event (sync)", 
                            error=str(e),
                            slack_message_id=slack_message_id,
                            exc_info=True)
            return False

    def should_process_event(self, event: Dict[str, Any]) -> bool:
        """
        Determina si un evento debe ser procesado basado en su tipo y subtipo.
        """
        # Solo procesar mensajes de tipo "message"
        if event.get("type") != "message":
            return False

        # Ignorar subtipos no deseados
        ignored_subtypes = [
            "message_deleted", 
            "message_changed", 
            "channel_join", 
            "bot_message"
        ]
        if event.get("subtype") in ignored_subtypes:
            return False

        # Ignorar mensajes de bots
        if event.get("bot_id"):
            return False

        return True

    def get_messages(
        self,
        skip: int = 0,
        limit: int = 100,
        team_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Obtener mensajes de Slack con filtros opcionales.
        """
        return get_slack_messages(
            session=self.session,
            skip=skip,
            limit=limit,
            team_id=team_id,
            channel_id=channel_id,
            user_id=user_id
        ) 