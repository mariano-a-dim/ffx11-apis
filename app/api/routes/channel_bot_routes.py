from fastapi import APIRouter, Request, Depends, HTTPException
from sqlmodel import Session
import hmac
import hashlib
import time
import json
from typing import Dict, Any

from app.core.config import settings
from app.api.deps import get_db
from app.services.channel_bot_service import ChannelBotService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/slack/channel-bot", tags=["channel-bot"])


def verify_slack_signature(request: Request, body: str) -> bool:
    """
    Verifica la firma de Slack para asegurar que la petición es legítima.
    """
    try:
        # Obtener headers necesarios
        timestamp = request.headers.get("x-slack-request-timestamp")
        signature = request.headers.get("x-slack-signature")
        
        if not timestamp or not signature:
            logger.warning("Missing Slack signature headers")
            return False
        
        # Verificar que la petición no sea muy antigua (5 minutos)
        if abs(time.time() - int(timestamp)) > 300:
            logger.warning("Request timestamp too old")
            return False
        
        # Crear la firma esperada
        sig_basestring = f"v0:{timestamp}:{body}"
        expected_signature = f"v0={hmac.new(settings.SLACK_SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()}"
        
        # Comparar firmas
        return hmac.compare_digest(expected_signature, signature)
        
    except Exception as e:
        logger.error(f"Error verifying Slack signature: {e}")
        return False


@router.post("/events")
async def channel_bot_events(request: Request, session: Session = Depends(get_db)):
    """
    Endpoint para recibir eventos del bot público del canal.
    Maneja eventos de message.channels y app_mention.
    """
    try:
        # Leer el body de la petición
        body = await request.body()
        body_str = body.decode('utf-8')
        
        # Verificar la firma de Slack
        if not verify_slack_signature(request, body_str):
            logger.warning("Invalid Slack signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parsear el JSON
        data = json.loads(body_str)
        
        # Log del evento recibido
        logger.info("Channel bot event received", 
                   event_type=data.get("type"),
                   event_keys=list(data.keys()))
        
        # Manejar verificación de URL
        if data.get("type") == "url_verification":
            logger.info("Channel bot URL verification")
            return {"challenge": data.get("challenge")}
        
        # Manejar eventos de callback
        if data.get("type") == "event_callback":
            event = data.get("event", {})
            event_type = event.get("type")
            
            logger.info("Channel bot event callback", 
                       event_type=event_type,
                       channel_id=event.get("channel"),
                       user_id=event.get("user"))
            
            if 'X-Slack-Retry-Num' in request.headers:
                logger.info("Slack retry detected", retry_num=request.headers['X-Slack-Retry-Num'])                
                retry_num = int(request.headers['X-Slack-Retry-Num'])
                if retry_num >= 1:
                    return {"status": "ok"}
            
            # Crear servicio del bot del canal
            bot_service = ChannelBotService(session=session)
            
            # Procesar según el tipo de evento
            if event_type == "message":
                await bot_service.handle_channel_message(event)
            elif event_type == "app_mention":
                await bot_service.handle_app_mention(event)
            else:
                logger.info(f"Unhandled event type: {event_type}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing channel bot event: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/test")
async def test_channel_bot():
    """
    Endpoint de prueba para verificar que el bot del canal está funcionando.
    """
    logger.info("Channel bot test endpoint called")
    return {
        "message": "Channel bot is working!",
        "timestamp": time.time(),
        "service": "channel-bot"
    }


@router.post("/config")
async def configure_channel_bot(
    channel_id: str,
    specialists: Dict[str, Any],
    session: Session = Depends(get_db)
):
    """
    Configurar especialistas para un canal específico.
    """
    try:
        bot_service = ChannelBotService(session=session)
        result = await bot_service.configure_channel(channel_id, specialists)
        
        logger.info("Channel bot configured", 
                   channel_id=channel_id,
                   specialists_count=len(specialists))
        
        return {
            "status": "success",
            "channel_id": channel_id,
            "specialists": result
        }
        
    except Exception as e:
        logger.error(f"Error configuring channel bot: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 