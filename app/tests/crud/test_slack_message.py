import pytest
from sqlmodel import Session

from app.core.exceptions import DatabaseException, ValidationException
from app.crud.slack_message import (
    create_slack_message,
    get_slack_message_by_id,
    get_slack_messages,
    update_slack_message,
    delete_slack_message,
    count_slack_messages
)
from app.models import SlackMessageCreate, SlackMessageUpdate


class TestSlackMessageCRUD:
    """Tests para las operaciones CRUD de mensajes de Slack."""

    def test_create_slack_message_success(self, db: Session):
        """Test crear mensaje de Slack exitosamente."""
        message_data = SlackMessageCreate(
            slack_message_id="1234567890.123456",
            team_id="T1234567890",
            channel_id="C1234567890",
            channel_name="test-channel",
            user_id="U1234567890",
            user_name="test_user",
            text="Test message",
            message_type="message",
            timestamp="1234567890.123456",
            raw_event={"type": "message", "text": "Test message"}
        )
        
        message = create_slack_message(session=db, slack_message_in=message_data)
        
        assert message is not None
        assert message.slack_message_id == "1234567890.123456"
        assert message.text == "Test message"
        assert message.team_id == "T1234567890"
        assert message.channel_id == "C1234567890"
        assert message.user_id == "U1234567890"
        assert message.channel_name == "test-channel"
        assert message.user_name == "test_user"
        assert message.message_type == "message"
        assert message.timestamp == "1234567890.123456"
        assert message.raw_event == {"type": "message", "text": "Test message"}
        assert message.is_bot is False
        assert message.is_ai_response is False

    def test_create_slack_message_with_bot(self, db: Session):
        """Test crear mensaje de bot."""
        message_data = SlackMessageCreate(
            slack_message_id="1234567890.123456",
            team_id="T1234567890",
            channel_id="C1234567890",
            user_id="U1234567890",
            text="Bot message",
            message_type="message",
            timestamp="1234567890.123456",
            is_bot=True,
            raw_event={"type": "message", "text": "Bot message", "bot_id": "B1234567890"}
        )
        
        message = create_slack_message(session=db, slack_message_in=message_data)
        
        assert message.is_bot is True

    def test_create_slack_message_with_files(self, db: Session):
        """Test crear mensaje con archivos."""
        message_data = SlackMessageCreate(
            slack_message_id="1234567890.123456",
            team_id="T1234567890",
            channel_id="C1234567890",
            user_id="U1234567890",
            text="Message with files",
            message_type="message",
            timestamp="1234567890.123456",
            files=[{"id": "F1234567890", "name": "test.txt"}],
            raw_event={"type": "message", "text": "Message with files"}
        )
        
        message = create_slack_message(session=db, slack_message_in=message_data)
        
        assert len(message.files) == 1
        assert message.files[0]["id"] == "F1234567890"
        assert message.files[0]["name"] == "test.txt"

    def test_create_slack_message_with_reactions(self, db: Session):
        """Test crear mensaje con reacciones."""
        message_data = SlackMessageCreate(
            slack_message_id="1234567890.123456",
            team_id="T1234567890",
            channel_id="C1234567890",
            user_id="U1234567890",
            text="Message with reactions",
            message_type="message",
            timestamp="1234567890.123456",
            reactions=[{"name": "thumbsup", "count": 2}],
            raw_event={"type": "message", "text": "Message with reactions"}
        )
        
        message = create_slack_message(session=db, slack_message_in=message_data)
        
        assert len(message.reactions) == 1
        assert message.reactions[0]["name"] == "thumbsup"
        assert message.reactions[0]["count"] == 2

    def test_get_slack_message_by_id_success(self, db: Session):
        """Test obtener mensaje por ID exitosamente."""
        # Crear mensaje
        message_data = SlackMessageCreate(
            slack_message_id="1234567890.123456",
            team_id="T1234567890",
            channel_id="C1234567890",
            user_id="U1234567890",
            text="Test message",
            message_type="message",
            timestamp="1234567890.123456",
            raw_event={"type": "message", "text": "Test message"}
        )
        created_message = create_slack_message(session=db, slack_message_in=message_data)
        
        # Obtener mensaje
        retrieved_message = get_slack_message_by_id(
            session=db, 
            slack_message_id="1234567890.123456"
        )
        
        assert retrieved_message is not None
        assert retrieved_message.id == created_message.id
        assert retrieved_message.text == "Test message"
        assert retrieved_message.slack_message_id == "1234567890.123456"

    def test_get_slack_message_by_id_not_found(self, db: Session):
        """Test obtener mensaje por ID que no existe."""
        message = get_slack_message_by_id(
            session=db, 
            slack_message_id="nonexistent.123456"
        )
        
        assert message is None

    def test_get_slack_messages_empty(self, db: Session):
        """Test obtener mensajes cuando no hay ninguno."""
        messages = get_slack_messages(session=db)
        
        assert len(messages) == 0

    def test_get_slack_messages_with_data(self, db: Session):
        """Test obtener mensajes con datos."""
        # Crear mensajes de prueba
        messages_data = [
            SlackMessageCreate(
                slack_message_id=f"1234567890.{i}",
                team_id="T1234567890",
                channel_id="C1234567890",
                user_id="U1234567890",
                text=f"Test message {i}",
                message_type="message",
                timestamp=f"1234567890.{i}",
                raw_event={"type": "message", "text": f"Test message {i}"}
            )
            for i in range(1, 4)
        ]
        
        for message_data in messages_data:
            create_slack_message(session=db, slack_message_in=message_data)
        
        # Obtener mensajes
        messages = get_slack_messages(session=db, skip=0, limit=10)
        
        assert len(messages) >= 3
        assert all(msg.team_id == "T1234567890" for msg in messages)
        assert all(msg.channel_id == "C1234567890" for msg in messages)

    def test_get_slack_messages_with_team_filter(self, db: Session):
        """Test obtener mensajes filtrados por equipo."""
        # Crear mensajes de diferentes equipos
        messages_data = [
            SlackMessageCreate(
                slack_message_id=f"1234567890.{i}",
                team_id="T1234567890" if i % 2 == 0 else "T9876543210",
                channel_id="C1234567890",
                user_id="U1234567890",
                text=f"Test message {i}",
                message_type="message",
                timestamp=f"1234567890.{i}",
                raw_event={"type": "message", "text": f"Test message {i}"}
            )
            for i in range(1, 6)
        ]
        
        for message_data in messages_data:
            create_slack_message(session=db, slack_message_in=message_data)
        
        # Obtener mensajes filtrados
        messages = get_slack_messages(session=db, team_id="T1234567890")
        
        assert all(msg.team_id == "T1234567890" for msg in messages)

    def test_get_slack_messages_with_channel_filter(self, db: Session):
        """Test obtener mensajes filtrados por canal."""
        # Crear mensajes de diferentes canales
        messages_data = [
            SlackMessageCreate(
                slack_message_id=f"1234567890.{i}",
                team_id="T1234567890",
                channel_id="C1234567890" if i % 2 == 0 else "C9876543210",
                user_id="U1234567890",
                text=f"Test message {i}",
                message_type="message",
                timestamp=f"1234567890.{i}",
                raw_event={"type": "message", "text": f"Test message {i}"}
            )
            for i in range(1, 6)
        ]
        
        for message_data in messages_data:
            create_slack_message(session=db, slack_message_in=message_data)
        
        # Obtener mensajes filtrados
        messages = get_slack_messages(session=db, channel_id="C1234567890")
        
        assert all(msg.channel_id == "C1234567890" for msg in messages)

    def test_get_slack_messages_with_user_filter(self, db: Session):
        """Test obtener mensajes filtrados por usuario."""
        # Crear mensajes de diferentes usuarios
        messages_data = [
            SlackMessageCreate(
                slack_message_id=f"1234567890.{i}",
                team_id="T1234567890",
                channel_id="C1234567890",
                user_id="U1234567890" if i % 2 == 0 else "U9876543210",
                text=f"Test message {i}",
                message_type="message",
                timestamp=f"1234567890.{i}",
                raw_event={"type": "message", "text": f"Test message {i}"}
            )
            for i in range(1, 6)
        ]
        
        for message_data in messages_data:
            create_slack_message(session=db, slack_message_in=message_data)
        
        # Obtener mensajes filtrados
        messages = get_slack_messages(session=db, user_id="U1234567890")
        
        assert all(msg.user_id == "U1234567890" for msg in messages)

    def test_get_slack_messages_pagination(self, db: Session):
        """Test paginación de mensajes."""
        # Crear 10 mensajes
        messages_data = [
            SlackMessageCreate(
                slack_message_id=f"1234567890.{i}",
                team_id="T1234567890",
                channel_id="C1234567890",
                user_id="U1234567890",
                text=f"Test message {i}",
                message_type="message",
                timestamp=f"1234567890.{i}",
                raw_event={"type": "message", "text": f"Test message {i}"}
            )
            for i in range(1, 11)
        ]
        
        for message_data in messages_data:
            create_slack_message(session=db, slack_message_in=message_data)
        
        # Obtener primera página
        messages_page1 = get_slack_messages(session=db, skip=0, limit=5)
        assert len(messages_page1) == 5
        
        # Obtener segunda página
        messages_page2 = get_slack_messages(session=db, skip=5, limit=5)
        assert len(messages_page2) == 5
        
        # Verificar que son diferentes mensajes
        page1_ids = {msg.slack_message_id for msg in messages_page1}
        page2_ids = {msg.slack_message_id for msg in messages_page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_get_slack_messages_invalid_skip(self, db: Session):
        """Test obtener mensajes con skip inválido."""
        with pytest.raises(ValidationException, match="skip must be >= 0"):
            get_slack_messages(session=db, skip=-1)

    def test_get_slack_messages_invalid_limit_zero(self, db: Session):
        """Test obtener mensajes con limit inválido (cero)."""
        with pytest.raises(ValidationException, match="limit must be between 1 and 1000"):
            get_slack_messages(session=db, limit=0)

    def test_get_slack_messages_invalid_limit_too_high(self, db: Session):
        """Test obtener mensajes con limit inválido (muy alto)."""
        with pytest.raises(ValidationException, match="limit must be between 1 and 1000"):
            get_slack_messages(session=db, limit=1001)

    def test_update_slack_message_success(self, db: Session):
        """Test actualizar mensaje exitosamente."""
        # Crear mensaje
        message_data = SlackMessageCreate(
            slack_message_id="1234567890.123456",
            team_id="T1234567890",
            channel_id="C1234567890",
            user_id="U1234567890",
            text="Original message",
            message_type="message",
            timestamp="1234567890.123456",
            raw_event={"type": "message", "text": "Original message"}
        )
        created_message = create_slack_message(session=db, slack_message_in=message_data)
        
        # Actualizar mensaje
        update_data = SlackMessageUpdate(
            text="Updated message",
            channel_name="updated-channel",
            user_name="updated_user"
        )
        
        updated_message = update_slack_message(
            session=db, 
            db_message=created_message, 
            message_in=update_data
        )
        
        assert updated_message.text == "Updated message"
        assert updated_message.channel_name == "updated-channel"
        assert updated_message.user_name == "updated_user"
        assert updated_message.team_id == "T1234567890"  # No debe cambiar

    def test_update_slack_message_partial(self, db: Session):
        """Test actualización parcial de mensaje."""
        # Crear mensaje
        message_data = SlackMessageCreate(
            slack_message_id="1234567890.123456",
            team_id="T1234567890",
            channel_id="C1234567890",
            user_id="U1234567890",
            text="Original message",
            message_type="message",
            timestamp="1234567890.123456",
            raw_event={"type": "message", "text": "Original message"}
        )
        created_message = create_slack_message(session=db, slack_message_in=message_data)
        
        # Actualizar solo el texto
        update_data = SlackMessageUpdate(text="Only text updated")
        
        updated_message = update_slack_message(
            session=db, 
            db_message=created_message, 
            message_in=update_data
        )
        
        assert updated_message.text == "Only text updated"
        assert updated_message.channel_name == "test-channel"  # No debe cambiar
        assert updated_message.user_name == "test_user"  # No debe cambiar

    def test_delete_slack_message_success(self, db: Session):
        """Test eliminar mensaje exitosamente."""
        # Crear mensaje
        message_data = SlackMessageCreate(
            slack_message_id="1234567890.123456",
            team_id="T1234567890",
            channel_id="C1234567890",
            user_id="U1234567890",
            text="Message to delete",
            message_type="message",
            timestamp="1234567890.123456",
            raw_event={"type": "message", "text": "Message to delete"}
        )
        create_slack_message(session=db, slack_message_in=message_data)
        
        # Eliminar mensaje
        result = delete_slack_message(session=db, slack_message_id="1234567890.123456")
        
        assert result is True
        
        # Verificar que fue eliminado
        deleted_message = get_slack_message_by_id(session=db, slack_message_id="1234567890.123456")
        assert deleted_message is None

    def test_delete_slack_message_not_found(self, db: Session):
        """Test eliminar mensaje que no existe."""
        result = delete_slack_message(session=db, slack_message_id="nonexistent.123456")
        
        assert result is False

    def test_count_slack_messages_empty(self, db: Session):
        """Test contar mensajes cuando no hay ninguno."""
        count = count_slack_messages(session=db)
        
        assert count == 0

    def test_count_slack_messages_with_data(self, db: Session):
        """Test contar mensajes con datos."""
        # Crear mensajes de prueba
        messages_data = [
            SlackMessageCreate(
                slack_message_id=f"1234567890.{i}",
                team_id="T1234567890",
                channel_id="C1234567890",
                user_id="U1234567890",
                text=f"Test message {i}",
                message_type="message",
                timestamp=f"1234567890.{i}",
                raw_event={"type": "message", "text": f"Test message {i}"}
            )
            for i in range(1, 6)
        ]
        
        for message_data in messages_data:
            create_slack_message(session=db, slack_message_in=message_data)
        
        # Contar mensajes
        count = count_slack_messages(session=db)
        
        assert count >= 5

    def test_count_slack_messages_with_filters(self, db: Session):
        """Test contar mensajes con filtros."""
        # Crear mensajes de diferentes equipos
        messages_data = [
            SlackMessageCreate(
                slack_message_id=f"1234567890.{i}",
                team_id="T1234567890" if i % 2 == 0 else "T9876543210",
                channel_id="C1234567890",
                user_id="U1234567890",
                text=f"Test message {i}",
                message_type="message",
                timestamp=f"1234567890.{i}",
                raw_event={"type": "message", "text": f"Test message {i}"}
            )
            for i in range(1, 11)
        ]
        
        for message_data in messages_data:
            create_slack_message(session=db, slack_message_in=message_data)
        
        # Contar mensajes filtrados
        count_team1 = count_slack_messages(session=db, team_id="T1234567890")
        count_team2 = count_slack_messages(session=db, team_id="T9876543210")
        
        assert count_team1 == 5  # Mensajes con índice par
        assert count_team2 == 5  # Mensajes con índice impar

    def test_count_slack_messages_multiple_filters(self, db: Session):
        """Test contar mensajes con múltiples filtros."""
        # Crear mensajes variados
        messages_data = [
            SlackMessageCreate(
                slack_message_id=f"1234567890.{i}",
                team_id="T1234567890",
                channel_id="C1234567890" if i % 2 == 0 else "C9876543210",
                user_id="U1234567890" if i % 3 == 0 else "U9876543210",
                text=f"Test message {i}",
                message_type="message",
                timestamp=f"1234567890.{i}",
                raw_event={"type": "message", "text": f"Test message {i}"}
            )
            for i in range(1, 13)
        ]
        
        for message_data in messages_data:
            create_slack_message(session=db, slack_message_in=message_data)
        
        # Contar con múltiples filtros
        count = count_slack_messages(
            session=db,
            team_id="T1234567890",
            channel_id="C1234567890",
            user_id="U1234567890"
        )
        
        # Debería contar solo los mensajes que cumplen todas las condiciones
        assert count == 2  # Mensajes con índice 3 y 9 (divisibles por 3 y pares)


# Fixtures para los tests
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