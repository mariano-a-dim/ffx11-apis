#!/usr/bin/env python3
"""
Tests para el sistema de respuestas programadas de Slack
"""

import asyncio
import json
import pytest
from sqlmodel import Session, create_engine
from app.core.config import settings
from app.services.slack_response_scheduler import SlackResponseScheduler


class TestSlackResponseScheduler:
    """Tests para el scheduler de respuestas de Slack."""
    
    @pytest.fixture
    def session(self):
        """Fixture para crear una sesión de base de datos."""
        engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
        session = Session(engine)
        yield session
        session.close()
    
    @pytest.fixture
    def scheduler(self, session):
        """Fixture para crear el scheduler."""
        return SlackResponseScheduler(session)
    
    def create_test_message(self, text: str, user_id: str = "U123456", channel_id: str = "C123456") -> dict:
        """Crea un mensaje de prueba"""
        return {
            "type": "message",
            "channel": channel_id,
            "user": user_id,
            "text": text,
            "ts": "1234567890.123456",
            "client_msg_id": f"test_{hash(text)}",
            "team": "T123456"
        }
    
    async def test_scheduled_responses(self, scheduler):
        """Prueba el sistema de respuestas programadas"""
        
        # Mensajes de prueba con diferentes urgencias
        test_cases = [
            {
                "message": self.create_test_message("@madim el servidor está caído"),
                "urgency": "high",
                "response": "¡Entendido! Voy a revisar el servidor inmediatamente. ¿Puedes darme más detalles sobre el error?",
                "description": "Alta urgencia - servidor caído"
            },
            {
                "message": self.create_test_message("@madim ¿puedes revisar el deploy?"),
                "urgency": "medium", 
                "response": "Claro, reviso el deploy en los próximos minutos. ¿Hay algo específico que deba verificar?",
                "description": "Media urgencia - deploy"
            },
            {
                "message": self.create_test_message("@madim ¿qué opinas del nuevo feature?"),
                "urgency": "low",
                "response": "Me parece interesante la propuesta. Cuando tenga un momento libre lo reviso con más detalle.",
                "description": "Baja urgencia - opinión"
            },
            {
                "message": self.create_test_message("@madim ¿cuándo sale la nueva versión?"),
                "urgency": "none",
                "response": "La nueva versión está programada para la próxima semana. Te aviso cuando esté lista.",
                "description": "Sin urgencia - consulta general"
            }
        ]
        
        print("🤖 Probando sistema de respuestas programadas")
        print("=" * 60)
        
        # Mostrar configuraciones de tiempo
        print("\n📅 Configuraciones de tiempo de respuesta:")
        for urgency in ["high", "medium", "low", "none"]:
            config = scheduler.get_urgency_response_time(urgency)
            print(f"  {urgency.upper()}: {config['description']}")
        
        print("\n" + "=" * 60)
        
        # Programar respuestas
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 Caso {i}: {test_case['description']}")
            print(f"   Urgencia: {test_case['urgency']}")
            print(f"   Mensaje: {test_case['message']['text']}")
            print(f"   Respuesta: {test_case['response'][:80]}...")
            
            # Programar respuesta
            scheduler.schedule_response(
                message=test_case['message'],
                urgency_level=test_case['urgency'],
                response=test_case['response'],
                team_id="T123456"
            )
            
            print(f"   ✅ Respuesta programada")
        
        print(f"\n⏰ Todas las respuestas han sido programadas")
        print("   Las respuestas se enviarán automáticamente según la urgencia")
        print("   Revisa los logs para ver el progreso")
    
    def test_urgency_response_times(self, scheduler):
        """Prueba la obtención de tiempos de respuesta por urgencia."""
        
        urgencies = ["high", "medium", "low", "none"]
        
        for urgency in urgencies:
            config = scheduler.get_urgency_response_time(urgency)
            
            assert config["urgency_level"] == urgency
            assert "min_minutes" in config
            assert "max_minutes" in config
            assert "description" in config
            
            print(f"✅ {urgency.upper()}: {config['description']}")
    
    def test_test_response_scheduling(self, scheduler):
        """Prueba el scheduling de respuestas de prueba."""
        
        test_message = self.create_test_message("Mensaje de prueba")
        test_response = "Esta es una respuesta de prueba"
        
        # Programar respuesta de prueba
        scheduler.schedule_test_response(
            message=test_message,
            response=test_response,
            team_id="T123456"
        )
        
        print("✅ Respuesta de prueba programada correctamente")
    
    def test_loco_response_scheduling(self, scheduler):
        """Prueba el scheduling de respuestas para mensajes con 'loco'."""
        
        test_message = self.create_test_message("@madim esto está loco")
        test_response = "¡Hola! 🎯 Detecté la palabra 'loco' en tu mensaje."
        
        # Programar respuesta de "loco"
        scheduler.schedule_loco_response(
            message=test_message,
            response=test_response,
            team_id="T123456"
        )
        
        print("✅ Respuesta de 'loco' programada correctamente")


# Función para ejecutar tests manualmente
async def run_manual_tests():
    """Ejecuta los tests manualmente para debugging."""
    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    session = Session(engine)
    scheduler = SlackResponseScheduler(session)
    
    test_instance = TestSlackResponseScheduler()
    await test_instance.test_scheduled_responses(scheduler)
    test_instance.test_urgency_response_times(scheduler)
    test_instance.test_test_response_scheduling(scheduler)
    test_instance.test_loco_response_scheduling(scheduler)
    
    session.close()


if __name__ == "__main__":
    asyncio.run(run_manual_tests()) 