import json
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from app.core.exceptions import DatabaseException, ValidationException
from app.models import SlackMessage, SlackMessageCreate, SlackMessageUpdate
from app.services.slack_service import SlackService


class TestSlackService:
    """Tests para el servicio de Slack."""

    def test_should_process_event_message(self, db: Session):
        """Test que un mensaje normal debe procesarse."""
        service = SlackService(session=db)
        event = {
            "type": "message",
            "user": "U1234567890",
            "text": "Hola mundo",
            "ts": "1234567890.123456",
            "channel": "C1234567890"
        }
        
        assert service.should_process_event(event) is True

    def test_should_process_event_bot_message(self, db: Session):
        """Test que un mensaje de bot no debe procesarse."""
        service = SlackService(session=db)
        event = {
            "type": "message",
            "bot_id": "B1234567890",
            "user": "U1234567890",
            "text": "Mensaje de bot",
            "ts": "1234567890.123456",
            "channel": "C1234567890"
        }
        
        assert service.should_process_event(event) is False

    def test_should_process_event_message_deleted(self, db: Session):
        """Test que un mensaje eliminado no debe procesarse."""
        service = SlackService(session=db)
        event = {
            "type": "message",
            "subtype": "message_deleted",
            "user": "U1234567890",
            "text": "Mensaje eliminado",
            "ts": "1234567890.123456",
            "channel": "C1234567890"
        }
        
        assert service.should_process_event(event) is False

    def test_should_process_event_channel_join(self, db: Session):
        """Test que un evento de unión a canal no debe procesarse."""
        service = SlackService(session=db)
        event = {
            "type": "message",
            "subtype": "channel_join",
            "user": "U1234567890",
            "text": "se unió al canal",
            "ts": "1234567890.123456",
            "channel": "C1234567890"
        }
        
        assert service.should_process_event(event) is False

    def test_should_process_event_not_message(self, db: Session):
        """Test que un evento que no es mensaje no debe procesarse."""
        service = SlackService(session=db)
        event = {
            "type": "reaction_added",
            "user": "U1234567890",
            "item": {"type": "message", "channel": "C1234567890", "ts": "1234567890.123456"},
            "reaction": "thumbsup"
        }
        
        assert service.should_process_event(event) is False

    @patch('app.services.slack_service.create_slack_message')
    @patch('app.services.slack_service.get_slack_messages')
    @patch('app.services.ai_service.AIService.analyze_message')
    @patch('app.services.ai_service.AIService.should_respond')
    def test_process_message_event_success(
        self, 
        mock_should_respond, 
        mock_analyze_message, 
        mock_get_messages, 
        mock_create_message, 
        db: Session
    ):
        """Test procesamiento exitoso de evento de mensaje."""
        # Configurar mocks
        mock_create_message.return_value = MagicMock(id="test-id")
        mock_get_messages.return_value = []
        mock_analyze_message.return_value = {
            "urgency": "low",
            "should_respond": False,
            "reasoning": "Mensaje casual"
        }
        mock_should_respond.return_value = False
        
        service = SlackService(session=db)
        event = {
            "type": "message",
            "user": "U1234567890",
            "text": "Hola mundo",
            "ts": "1234567890.123456",
            "channel": "C1234567890",
            "client_msg_id": "test-msg-id"
        }
        team_id = "T1234567890"
        
        result = service.process_message_event(event, team_id)
        
        assert result is True
        mock_create_message.assert_called_once()
        mock_analyze_message.assert_called_once()

    @patch('app.services.slack_service.get_slack_message_by_id')
    def test_process_message_event_duplicate(self, mock_get_message, db: Session):
        """Test procesamiento de mensaje duplicado."""
        # Configurar mock para simular mensaje existente
        mock_get_message.return_value = MagicMock()
        
        service = SlackService(session=db)
        event = {
            "type": "message",
            "user": "U1234567890",
            "text": "Mensaje duplicado",
            "ts": "1234567890.123456",
            "channel": "C1234567890",
            "client_msg_id": "duplicate-msg-id"
        }
        team_id = "T1234567890"
        
        result = service.process_message_event(event, team_id)
        
        assert result is True
        mock_get_message.assert_called_once()

    @patch('app.services.slack_service.create_slack_message')
    def test_process_message_event_database_error(self, mock_create_message, db: Session):
        """Test error de base de datos en procesamiento."""
        # Configurar mock para lanzar excepción
        mock_create_message.side_effect = DatabaseException("DB error")
        
        service = SlackService(session=db)
        event = {
            "type": "message",
            "user": "U1234567890",
            "text": "Mensaje con error",
            "ts": "1234567890.123456",
            "channel": "C1234567890",
            "client_msg_id": "error-msg-id"
        }
        team_id = "T1234567890"
        
        result = service.process_message_event(event, team_id)
        
        assert result is False

    def test_get_messages(self, db: Session):
        """Test obtener mensajes del servicio."""
        service = SlackService(session=db)
        
        with patch('app.services.slack_service.get_slack_messages') as mock_get:
            mock_get.return_value = []
            result = service.get_messages(skip=0, limit=10)
            
            assert result == []
            mock_get.assert_called_once_with(
                session=db, skip=0, limit=10, 
                team_id=None, channel_id=None, user_id=None
            )

    def test_get_messages_with_filters(self, db: Session):
        """Test obtener mensajes con filtros."""
        service = SlackService(session=db)
        
        with patch('app.services.slack_service.get_slack_messages') as mock_get:
            mock_get.return_value = []
            result = service.get_messages(
                skip=5, 
                limit=20, 
                team_id="T1234567890",
                channel_id="C1234567890",
                user_id="U1234567890"
            )
            
            assert result == []
            mock_get.assert_called_once_with(
                session=db, skip=5, limit=20,
                team_id="T1234567890", 
                channel_id="C1234567890", 
                user_id="U1234567890"
            )


class TestSlackOAuthService:
    """Tests para el servicio de OAuth de Slack."""

    @patch('app.services.slack_oauth_service.httpx.AsyncClient.post')
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self, mock_post):
        """Test intercambio exitoso de código por token."""
        from app.services.slack_oauth_service import SlackOAuthService
        
        # Configurar mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "access_token": "xoxb-test-token",
            "team": {"id": "T1234567890", "name": "Test Team"},
            "authed_user": {"id": "U1234567890", "name": "test_user"}
        }
        mock_post.return_value = mock_response
        
        service = SlackOAuthService()
        result = await service.exchange_code_for_token("test_code")
        
        assert result["ok"] is True
        assert result["access_token"] == "xoxb-test-token"
        assert result["team"]["id"] == "T1234567890"

    @patch('app.services.slack_oauth_service.httpx.AsyncClient.post')
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_failure(self, mock_post):
        """Test fallo en intercambio de código por token."""
        from app.services.slack_oauth_service import SlackOAuthService
        from app.core.exceptions import SlackException
        
        # Configurar mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": False,
            "error": "invalid_code"
        }
        mock_post.return_value = mock_response
        
        service = SlackOAuthService()
        
        with pytest.raises(SlackException):
            await service.exchange_code_for_token("invalid_code")

    @patch('app.services.slack_oauth_service.httpx.AsyncClient.post')
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_http_error(self, mock_post):
        """Test error HTTP en intercambio de código."""
        from app.services.slack_oauth_service import SlackOAuthService
        from app.core.exceptions import SlackException
        
        # Configurar mock para lanzar excepción HTTP
        mock_post.side_effect = Exception("HTTP Error")
        
        service = SlackOAuthService()
        
        with pytest.raises(SlackException):
            await service.exchange_code_for_token("test_code")

    def test_get_access_token(self):
        """Test extraer token de acceso."""
        from app.services.slack_oauth_service import SlackOAuthService
        
        service = SlackOAuthService()
        oauth_data = {
            "access_token": "xoxb-test-token",
            "team": {"id": "T1234567890", "name": "Test Team"},
            "authed_user": {"id": "U1234567890", "name": "test_user"}
        }
        
        token = service.get_access_token(oauth_data)
        assert token == "xoxb-test-token"

    def test_get_access_token_missing(self):
        """Test extraer token de acceso faltante."""
        from app.services.slack_oauth_service import SlackOAuthService
        
        service = SlackOAuthService()
        oauth_data = {
            "team": {"id": "T1234567890", "name": "Test Team"},
            "authed_user": {"id": "U1234567890", "name": "test_user"}
        }
        
        token = service.get_access_token(oauth_data)
        assert token is None

    def test_get_team_info(self):
        """Test extraer información del equipo."""
        from app.services.slack_oauth_service import SlackOAuthService
        
        service = SlackOAuthService()
        oauth_data = {
            "access_token": "xoxb-test-token",
            "team": {"id": "T1234567890", "name": "Test Team"},
            "authed_user": {"id": "U1234567890", "name": "test_user"}
        }
        
        team_info = service.get_team_info(oauth_data)
        assert team_info["id"] == "T1234567890"
        assert team_info["name"] == "Test Team"

    def test_get_team_info_missing(self):
        """Test extraer información del equipo faltante."""
        from app.services.slack_oauth_service import SlackOAuthService
        
        service = SlackOAuthService()
        oauth_data = {
            "access_token": "xoxb-test-token",
            "authed_user": {"id": "U1234567890", "name": "test_user"}
        }
        
        team_info = service.get_team_info(oauth_data)
        assert team_info == {}

    def test_get_user_info(self):
        """Test extraer información del usuario."""
        from app.services.slack_oauth_service import SlackOAuthService
        
        service = SlackOAuthService()
        oauth_data = {
            "access_token": "xoxb-test-token",
            "team": {"id": "T1234567890", "name": "Test Team"},
            "authed_user": {"id": "U1234567890", "name": "test_user"}
        }
        
        user_info = service.get_user_info(oauth_data)
        assert user_info["id"] == "U1234567890"
        assert user_info["name"] == "test_user"

    def test_get_user_info_missing(self):
        """Test extraer información del usuario faltante."""
        from app.services.slack_oauth_service import SlackOAuthService
        
        service = SlackOAuthService()
        oauth_data = {
            "access_token": "xoxb-test-token",
            "team": {"id": "T1234567890", "name": "Test Team"}
        }
        
        user_info = service.get_user_info(oauth_data)
        assert user_info == {}


class TestAIService:
    """Tests para el servicio de IA."""

    @patch('app.services.ai_service.ChatOpenAI')
    def test_analyze_message_success(self, mock_chat_openai):
        """Test análisis exitoso de mensaje."""
        from app.services.ai_service import AIService
        
        # Configurar mock
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = json.dumps({
            "urgency": "low",
            "should_respond": False,
            "reasoning": "Mensaje casual que no requiere respuesta"
        })
        mock_chat_openai.return_value = mock_llm
        
        service = AIService()
        event = {
            "type": "message",
            "user": "U1234567890",
            "text": "Hola, ¿cómo estás?",
            "ts": "1234567890.123456",
            "channel": "C1234567890"
        }
        conversation_context = []
        
        result = service.analyze_message(event, conversation_context)
        
        assert "urgency" in result
        assert "should_respond" in result
        assert "reasoning" in result
        assert result["urgency"] == "low"
        assert result["should_respond"] is False

    @patch('app.services.ai_service.ChatOpenAI')
    def test_analyze_message_invalid_json(self, mock_chat_openai):
        """Test análisis con JSON inválido en respuesta."""
        from app.services.ai_service import AIService
        
        # Configurar mock para devolver JSON inválido
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "invalid json"
        mock_chat_openai.return_value = mock_llm
        
        service = AIService()
        event = {
            "type": "message",
            "user": "U1234567890",
            "text": "Hola",
            "ts": "1234567890.123456",
            "channel": "C1234567890"
        }
        conversation_context = []
        
        result = service.analyze_message(event, conversation_context)
        
        # Debe devolver valores por defecto
        assert result["urgency"] == "low"
        assert result["should_respond"] is False
        assert "error" in result["reasoning"]

    @patch('app.services.ai_service.ChatOpenAI')
    def test_analyze_message_api_error(self, mock_chat_openai):
        """Test error de API en análisis."""
        from app.services.ai_service import AIService
        
        # Configurar mock para lanzar excepción
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API Error")
        mock_chat_openai.return_value = mock_llm
        
        service = AIService()
        event = {
            "type": "message",
            "user": "U1234567890",
            "text": "Hola",
            "ts": "1234567890.123456",
            "channel": "C1234567890"
        }
        conversation_context = []
        
        result = service.analyze_message(event, conversation_context)
        
        # Debe devolver valores por defecto
        assert result["urgency"] == "low"
        assert result["should_respond"] is False
        assert "error" in result["reasoning"]

    def test_should_respond_true(self):
        """Test que debe responder cuando urgency es high."""
        from app.services.ai_service import AIService
        
        service = AIService()
        analysis = {
            "urgency": "high",
            "should_respond": True,
            "reasoning": "Mensaje urgente que requiere respuesta"
        }
        
        assert service.should_respond(analysis) is True

    def test_should_respond_false(self):
        """Test que no debe responder cuando urgency es low."""
        from app.services.ai_service import AIService
        
        service = AIService()
        analysis = {
            "urgency": "low",
            "should_respond": False,
            "reasoning": "Mensaje casual"
        }
        
        assert service.should_respond(analysis) is False

    def test_should_respond_medium(self):
        """Test que debe responder cuando urgency es medium."""
        from app.services.ai_service import AIService
        
        service = AIService()
        analysis = {
            "urgency": "medium",
            "should_respond": True,
            "reasoning": "Mensaje moderadamente urgente"
        }
        
        assert service.should_respond(analysis) is True

    def test_should_respond_missing_urgency(self):
        """Test que no debe responder cuando falta urgency."""
        from app.services.ai_service import AIService
        
        service = AIService()
        analysis = {
            "should_respond": False,
            "reasoning": "Mensaje sin urgencia"
        }
        
        assert service.should_respond(analysis) is False


# Fixtures para los tests
@pytest.fixture
def sample_slack_event():
    """Evento de ejemplo de Slack."""
    return {
        "type": "event_callback",
        "event_id": "Ev1234567890",
        "team_id": "T1234567890",
        "event": {
            "type": "message",
            "user": "U1234567890",
            "text": "Hola, esto es una prueba",
            "ts": "1234567890.123456",
            "channel": "C1234567890",
            "event_ts": "1234567890.123456",
            "channel_type": "channel"
        },
        "event_time": 1234567890
    }

@pytest.fixture
def sample_slack_message_data():
    """Datos de ejemplo para mensajes de Slack."""
    return {
        "slack_message_id": "1234567890.123456",
        "team_id": "T1234567890",
        "channel_id": "C1234567890",
        "channel_name": "test-channel",
        "user_id": "U1234567890",
        "user_name": "test_user",
        "text": "Test message",
        "message_type": "message",
        "timestamp": "1234567890.123456",
        "raw_event": {"type": "message", "text": "Test message"}
    } 