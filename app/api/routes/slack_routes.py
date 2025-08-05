from fastapi import APIRouter, Request, Depends, Query
from sqlmodel import Session
from typing import List, Optional
from datetime import datetime

from app.core.config import settings
from app.api.deps import get_db, CurrentUser, get_current_active_superuser
from app.services.slack_service import SlackService
from app.services.slack_oauth_service import SlackOAuthService
from app.core.exceptions import SlackException
from app.core.logging import get_logger

from app.models import SlackMessagePublic, SlackMessagesPublic
from app.services.slack_response_scheduler import SlackResponseScheduler

# Inicializar logger
logger = get_logger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])


@router.get("/test")
async def test_slack_route():
    """
    Test endpoint to verify Slack routes are working.
    """
    logger.info("Slack test endpoint called")
    logger.warning("This is a warning test")
    logger.error("This is an error test")
    return {"message": "Slack routes are working!"}


@router.get("/test-mentions")
async def test_mentions_processing(session: Session = Depends(get_db)):
    """
    Test endpoint to verify mentions processing is working.
    """
    logger.info("Testing mentions processing")
    
    # Verificar configuración
    access_token = settings.SLACK_PERSONAL_TOKEN
    has_token = bool(access_token)
    token_preview = access_token[:10] + "..." if access_token else None
    
    # Crear servicio y probar procesamiento
    slack_service = SlackService(session=session)
    
    # Texto de prueba
    test_text = "<@U036PD91RR6> holaaaa"
    
    try:
        processed_text = await slack_service.user_service.process_message_text(test_text, access_token or "test-token")
        success = True
    except Exception as e:
        processed_text = str(e)
        success = False
    
    # Limpiar cache para probar con nueva configuración
    slack_service.user_service.clear_cache()
    
    # Obtener información detallada del usuario para debugging
    user_info = None
    if success and access_token:
        try:
            user_info = await slack_service.user_service.get_user_info("U036PD91RR6", access_token)
        except Exception as e:
            user_info = {"error": str(e)}
    
    return {
        "has_token": has_token,
        "token_preview": token_preview,
        "test_text": test_text,
        "processed_text": processed_text,
        "success": success,
        "cache_stats": slack_service.user_service.get_cache_stats(),
        "user_info_debug": {
            "name": user_info.get("name") if user_info else None,
            "real_name": user_info.get("profile", {}).get("real_name") if user_info else None,
            "display_name": user_info.get("profile", {}).get("display_name") if user_info else None,
            "first_name": user_info.get("profile", {}).get("first_name") if user_info else None,
            "last_name": user_info.get("profile", {}).get("last_name") if user_info else None,
            "full_user_info": user_info
        } if user_info else None
    }


@router.get("/test-token")
async def test_slack_token():
    """
    Test endpoint to verify Slack token is working.
    """
    import httpx
    
    access_token = settings.SLACK_PERSONAL_TOKEN
    if not access_token:
        return {"error": "No token configured"}
    
    # Mostrar información del token para debugging
    token_info = {
        "token_length": len(access_token) if access_token else 0,
        "token_starts_with": access_token[:20] if access_token else None,
        "token_ends_with": access_token[-10:] if access_token else None,
        "contains_xoxp": "xoxp-" in access_token if access_token else False,
        "contains_xoxb": "xoxb-" in access_token if access_token else False,
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Test auth.test endpoint first
            auth_response = await client.get(
                "https://slack.com/api/auth.test",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            auth_data = auth_response.json()
            
            # Test users.info endpoint
            user_response = await client.get(
                "https://slack.com/api/users.info",
                params={"user": "U036PD91RR6"},
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            user_data = user_response.json()
            
            return {
                "token_info": token_info,
                "auth_test": {
                    "status_code": auth_response.status_code,
                    "ok": auth_data.get("ok"),
                    "error": auth_data.get("error"),
                    "user_id": auth_data.get("user_id"),
                    "team_id": auth_data.get("team_id")
                },
                "user_info": {
                    "status_code": user_response.status_code,
                    "ok": user_data.get("ok"),
                    "error": user_data.get("error"),
                    "user": user_data.get("user", {}).get("name") if user_data.get("ok") else None
                }
            }
            
    except Exception as e:
        return {"error": str(e), "token_info": token_info}


@router.get("/test-scheduler")
async def test_scheduler(session: Session = Depends(get_db)):
    """
    Endpoint de prueba para verificar el funcionamiento del scheduler.
    Programa una respuesta de prueba que se enviará en 30 segundos.
    """
    try:
        from app.services.slack_response_scheduler import SlackResponseScheduler
        from app.core.config import settings
        
        # Verificar token
        access_token = settings.SLACK_PERSONAL_TOKEN
        if not access_token:
            return {
                "success": False,
                "error": "No Slack token configured"
            }
        
        # Crear scheduler
        scheduler = SlackResponseScheduler(session)
        
        # Mensaje de prueba
        test_message = {
            "channel": "D035ZLDLY5R",  # Canal de DM
            "text": "Mensaje de prueba para scheduler",
            "thread_ts": None
        }
        
        test_response = "🧪 Esta es una respuesta de prueba del scheduler. Se programó para enviarse con delay."
        
        # Programar respuesta de prueba usando configuración del .env
        scheduler.schedule_test_response(
            message=test_message,
            response=test_response,
            team_id="TM7GUP8DU"
        )
        
        return {
            "success": True,
            "message": "Test response scheduled",
            "details": {
                "channel": test_message["channel"],
                "response_preview": test_response[:50],
                "urgency_level": "test",
                "expected_delay": f"{settings.RESPONSE_DELAY_TEST} seconds",
                "scheduled_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error("Error in test scheduler", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/messages", response_model=SlackMessagesPublic, dependencies=[Depends(get_current_active_superuser)])
async def get_messages(
    session: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    team_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None)
):
    """
    Obtener mensajes de Slack con filtros opcionales.
    """
    logger.info("Getting Slack messages", 
               skip=skip, limit=limit, team_id=team_id, 
               channel_id=channel_id, user_id=user_id)
    
    slack_service = SlackService(session=session)
    messages = slack_service.get_messages(
        skip=skip,
        limit=limit,
        team_id=team_id,
        channel_id=channel_id,
        user_id=user_id
    )
    
    logger.info("Slack messages retrieved", count=len(messages))
    return SlackMessagesPublic(
        data=[SlackMessagePublic.model_validate(msg) for msg in messages],
        count=len(messages)
    )


@router.post("/events")
async def slack_events(request: Request, session: Session = Depends(get_db)):
    try:
        body = await request.json()
        
        # Log del mensaje completo que llega
        logger.info("Slack webhook received", 
                   body_type=body.get("type"),
                   body_keys=list(body.keys()),
                   full_body=body)

        # Verificación inicial de Slack (challenge)
        if body.get("type") == "url_verification":
            logger.info("Slack URL verification received")
            return {"challenge": body.get("challenge")}

        # Evento nuevo
        if body.get("type") == "event_callback":
            event = body["event"]
            team_id = body.get("team_id", "unknown")
            
            logger.info("Slack event received", 
                       event_type=event.get("type"),
                       team_id=team_id,
                       event_data=event)

            # Usar el servicio para procesar el evento
            slack_service = SlackService(session=session)
            
            if slack_service.should_process_event(event):
                # Obtener access token desde configuración
                access_token = settings.SLACK_PERSONAL_TOKEN
                logger.info("Processing event with access token", 
                           has_token=bool(access_token),
                           token_preview=access_token[:10] + "..." if access_token else None)
                
                try:
                    success = await slack_service.process_message_event(event, team_id, access_token)
                    if success:
                        logger.info("Event processed successfully with mentions", 
                                   event_type=event.get("type"))
                    else:
                        logger.error("Failed to process event with mentions", 
                                   event_type=event.get("type"))
                except Exception as e:
                    logger.error("Error processing event with mentions", 
                               event_type=event.get("type"), 
                               error=str(e),
                               error_type=type(e).__name__,
                               exc_info=True)
                    # Fallback a procesamiento síncrono sin menciones
                    logger.info("Falling back to sync processing without mentions")
                    success = slack_service.process_message_event_sync(event, team_id)
                    if success:
                        logger.info("Event processed successfully (fallback)", 
                                   event_type=event.get("type"))
                    else:
                        logger.error("Failed to process event (fallback)", 
                                   event_type=event.get("type"))
            else:
                logger.info("Event skipped - not processable", 
                           event_type=event.get("type"))

        return {"ok": True}
        
    except Exception as e:
        # Manejar ClientDisconnect y otros errores de conexión silenciosamente
        if "ClientDisconnect" in str(e) or "Connection closed" in str(e):
            logger.debug("Slack webhook connection closed normally", 
                        error_type=type(e).__name__)
            return {"ok": True}
        else:
            # Para otros errores, loggear pero no fallar
            logger.warning("Unexpected error in Slack webhook", 
                          error=str(e), 
                          error_type=type(e).__name__)
            return {"ok": True}


@router.get("/oauth/callback")
async def oauth_callback(request: Request):
    """
    OAuth callback endpoint for Slack integration.
    """
    logger.info("OAuth callback received")
    
    try:
        code = request.query_params.get("code")
        oauth_service = SlackOAuthService()
        
        # Intercambiar código por token
        oauth_data = await oauth_service.exchange_code_for_token(code)
        
        # Extraer token de acceso
        access_token = oauth_service.get_access_token(oauth_data)
        
        logger.info("OAuth callback successful")
        return {
            "access_token": access_token,
            "team_info": oauth_service.get_team_info(oauth_data),
            "user_info": oauth_service.get_user_info(oauth_data)
        }
        
    except SlackException as e:
        logger.error("OAuth callback failed - SlackException", error=str(e))
        raise e
    except Exception as e:
        logger.error("OAuth callback failed - unexpected error", error=str(e), exc_info=True)
        raise SlackException(f"Unexpected error: {str(e)}")


@router.get("/response-times", dependencies=[Depends(get_current_active_superuser)])
async def get_response_times(session: Session = Depends(get_db)):
    """
    Obtiene las configuraciones de tiempo de respuesta por nivel de urgencia.
    """
    try:
        from app.services.slack_response_scheduler import SlackResponseScheduler
        
        scheduler = SlackResponseScheduler(session)
        
        # Obtener tiempos del scheduler
        response_times = {}
        for urgency in ["high", "medium", "low", "none"]:
            response_times[urgency] = scheduler.get_urgency_response_time(urgency)
        
        # Obtener configuración actual del .env
        current_config = {
            "RESPONSE_DELAY_HIGH": settings.RESPONSE_DELAY_HIGH,
            "RESPONSE_DELAY_MEDIUM": settings.RESPONSE_DELAY_MEDIUM,
            "RESPONSE_DELAY_LOW": settings.RESPONSE_DELAY_LOW,
            "RESPONSE_DELAY_LOCO": settings.RESPONSE_DELAY_LOCO,
            "RESPONSE_DELAY_TEST": settings.RESPONSE_DELAY_TEST
        }
        
        return {
            "success": True,
            "current_config": current_config,
            "response_times": response_times,
            "description": "Configuración actual de delays y tiempos de respuesta programados"
        }
        
    except Exception as e:
        logger.error("Error getting response times", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }
