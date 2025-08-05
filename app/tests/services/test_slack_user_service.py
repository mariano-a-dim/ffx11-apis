#!/usr/bin/env python3
"""
Tests para el procesamiento de menciones de usuario en Slack.
"""

import asyncio
import sys
import os
import pytest

# Agregar el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app'))

from app.services.slack_user_service import SlackUserService
from app.core.config import settings
from sqlmodel import Session, create_engine


class TestSlackUserService:
    """Tests para el servicio de usuarios de Slack."""
    
    @pytest.fixture
    def session(self):
        """Fixture para crear una sesión de base de datos."""
        engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
        session = Session(engine)
        yield session
        session.close()
    
    @pytest.fixture
    def user_service(self, session):
        """Fixture para crear el servicio de usuarios."""
        return SlackUserService(session)
    
    async def test_user_mentions_processing(self, user_service):
        """Prueba el procesamiento de menciones de usuario."""
        
        print("🧪 Probando procesamiento de menciones de usuario...")
        
        # Casos de prueba
        test_cases = [
            {
                "text": "Hola <@U036PD91RR6>, ¿cómo estás?",
                "description": "Mensaje con mención simple"
            },
            {
                "text": "Necesito ayuda de <@U036PD91RR6> y <@U1234567890>",
                "description": "Mensaje con múltiples menciones"
            },
            {
                "text": "Este es un mensaje normal sin menciones",
                "description": "Mensaje sin menciones"
            },
            {
                "text": "Mencionando a <@U036PD91RR6> en un canal <#C1234567890|general>",
                "description": "Mensaje con mención de usuario y canal"
            }
        ]
        
        # Simular access token (en producción vendría de la configuración)
        access_token = settings.SLACK_PERSONAL_TOKEN
        
        if not access_token:
            print("⚠️  No hay SLACK_PERSONAL_TOKEN configurado. Usando modo simulación...")
            access_token = "xoxp-simulated-token"
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 Caso {i}: {test_case['description']}")
            print(f"   Texto original: {test_case['text']}")
            
            try:
                # Extraer menciones
                mentions = user_service.extract_user_mentions(test_case['text'])
                print(f"   Menciones encontradas: {mentions}")
                
                # Procesar texto (esto haría llamadas a la API de Slack si tuviera token válido)
                processed_text = await user_service.process_message_text(
                    test_case['text'], 
                    access_token
                )
                print(f"   Texto procesado: {processed_text}")
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
        
        print("\n✅ Pruebas completadas!")
    
    def test_regex_patterns(self, user_service):
        """Prueba los patrones regex para extraer menciones."""
        
        print("\n🔍 Probando patrones regex...")
        
        test_patterns = [
            "<@U036PD91RR6>",
            "<@U1234567890>",
            "<@ABC123DEF>",
            "Hola <@U036PD91RR6>, ¿cómo estás?",
            "Mencionando a <@U036PD91RR6> y <@U1234567890>",
            "Sin menciones aquí",
            "<#C1234567890|general>",
            "Canal <#C1234567890|general> y usuario <@U036PD91RR6>"
        ]
        
        for pattern in test_patterns:
            mentions = user_service.extract_user_mentions(pattern)
            print(f"   Texto: {pattern}")
            print(f"   Menciones: {mentions}")
            print()
        
        print("✅ Pruebas de regex completadas!")


# Función para ejecutar tests manualmente
async def run_manual_tests():
    """Ejecuta los tests manualmente para debugging."""
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    session = Session(engine)
    user_service = SlackUserService(session)
    
    test_instance = TestSlackUserService()
    await test_instance.test_user_mentions_processing(user_service)
    test_instance.test_regex_patterns(user_service)
    
    session.close()


if __name__ == "__main__":
    asyncio.run(run_manual_tests()) 