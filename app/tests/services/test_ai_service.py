#!/usr/bin/env python3
"""
Tests para el flujo de IA con LangGraph
"""

import asyncio
import json
import pytest
from sqlmodel import Session, create_engine
from app.core.config import settings
from app.services.ai_service import AIService
from app.models.slack import SlackMessageCreate
from app.crud.slack_message import create_slack_message


class TestAIService:
    """Tests para el servicio de IA."""
    
    @pytest.fixture
    def session(self):
        """Fixture para crear una sesión de base de datos."""
        engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
        session = Session(engine)
        yield session
        session.close()
    
    @pytest.fixture
    def ai_service(self, session):
        """Fixture para crear el servicio de IA."""
        return AIService(session)
    
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
    
    def test_ai_workflow(self, ai_service):
        """Prueba el flujo completo de IA"""
        
        # Mensajes de prueba con diferentes niveles de urgencia
        test_messages = [
            {
                "text": "@madim el servidor de producción está caído, clientes no pueden acceder",
                "user_id": "U789012",
                "description": "Alta urgencia - problema crítico de producción"
            },
            {
                "text": "@madim ¿puedes revisar el deploy de producción?",
                "user_id": "U789012",
                "description": "Media urgencia - deploy de producción"
            },
            {
                "text": "Hola equipo, ¿cómo va todo?",
                "user_id": "U345678", 
                "description": "Baja urgencia - mensaje general"
            },
            {
                "text": "Madim, necesito tu aprobación para el nuevo feature",
                "user_id": "U901234",
                "description": "Media urgencia - aprobación requerida"
            },
            {
                "text": "@madim hay un bug crítico que está afectando las ventas",
                "user_id": "U567890",
                "description": "Alta urgencia - bug que afecta ingresos"
            },
            {
                "text": "¿Alguien sabe cuándo sale la nueva versión?",
                "user_id": "U567890",
                "description": "Baja urgencia - consulta general"
            }
        ]
        
        print("🤖 Probando flujo de IA con LangGraph")
        print("=" * 50)
        
        for i, test_msg in enumerate(test_messages, 1):
            print(f"\n📝 Prueba {i}: {test_msg['description']}")
            print(f"Mensaje: {test_msg['text']}")
            
            # Crear mensaje de prueba
            message = self.create_test_message(
                text=test_msg['text'],
                user_id=test_msg['user_id']
            )
            
            # Analizar mensaje
            analysis = ai_service.analyze_message(message)
            
            print(f"📊 Análisis:")
            print(f"  - Es directo: {analysis.get('is_direct', False)}")
            print(f"  - Requiere respuesta: {analysis.get('requires_response', False)}")
            print(f"  - Razón: {analysis.get('reasoning', 'N/A')}")
            
            # Mostrar información de urgencia si está disponible
            if 'urgency_analysis' in analysis:
                urgency = analysis['urgency_analysis']
                print(f"🚨 Análisis de Urgencia:")
                print(f"  - Nivel: {urgency.get('urgency_level', 'unknown')}")
                print(f"  - Score: {urgency.get('urgency_score', 0)}")
                print(f"  - Factores: {', '.join(urgency.get('urgency_factors', []))}")
                print(f"  - Razón: {urgency.get('reasoning', 'N/A')}")
            else:
                print(f"  - Urgencia: {analysis.get('urgency', 'low')}")
            
            # Verificar si debe responder
            should_respond = ai_service.should_respond(analysis)
            print(f"🤔 Debe responder: {should_respond}")
            
            if should_respond:
                # Generar respuesta
                response = ai_service.get_response(message)
                print(f"💬 Respuesta generada: {response[:100] if response else 'None'}...")
            else:
                print("⏭️  No requiere respuesta")
            
            print("-" * 30)
    
    def test_loco_keyword_detection(self, ai_service):
        """Prueba la detección de la palabra 'loco'."""
        
        test_cases = [
            {
                "text": "@madim esto está loco, necesito ayuda",
                "expected_response": True,
                "description": "Mensaje con 'loco'"
            },
            {
                "text": "@madim el servidor está caído",
                "expected_response": False,
                "description": "Mensaje sin 'loco'"
            },
            {
                "text": "Esto está LOCO, necesito ayuda urgente",
                "expected_response": True,
                "description": "Mensaje con 'LOCO' en mayúsculas"
            }
        ]
        
        print("🎯 Probando detección de palabra 'loco'")
        print("=" * 40)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 Caso {i}: {test_case['description']}")
            print(f"Mensaje: {test_case['text']}")
            
            message = self.create_test_message(test_case['text'])
            analysis = ai_service.analyze_message(message)
            should_respond = ai_service.should_respond(analysis)
            
            print(f"Debería responder: {test_case['expected_response']}")
            print(f"Responde: {should_respond}")
            print(f"✅ {'Correcto' if should_respond == test_case['expected_response'] else '❌ Incorrecto'}")
    
    def test_sensitivity_detection(self, ai_service):
        """Prueba la detección de situaciones sensibles."""
        
        test_cases = [
            {
                "text": "@madim no puedo creer que Juan haya hecho eso otra vez. Estoy súper molesto",
                "description": "Situación sensible - conflicto personal"
            },
            {
                "text": "@madim ¿puedes revisar el código?",
                "description": "Situación normal - consulta técnica"
            },
            {
                "text": "@madim estoy muy frustrado con el equipo, siempre hacen lo mismo",
                "description": "Situación sensible - frustración con equipo"
            }
        ]
        
        print("🚫 Probando detección de situaciones sensibles")
        print("=" * 50)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 Caso {i}: {test_case['description']}")
            print(f"Mensaje: {test_case['text']}")
            
            message = self.create_test_message(test_case['text'])
            analysis = ai_service.analyze_message(message)
            should_respond = ai_service.should_respond(analysis)
            
            if should_respond:
                response = ai_service.get_response(message)
                print(f"Respuesta: {response[:100] if response else 'None'}...")
                
                # Verificar si es una respuesta de evasión
                if response and any(phrase in response.lower() for phrase in ["después", "más tarde", "lo reviso"]):
                    print("✅ Respuesta de evasión detectada")
                else:
                    print("ℹ️  Respuesta normal")
            else:
                print("⏭️  No requiere respuesta")


# Función para ejecutar tests manualmente
def run_manual_tests():
    """Ejecuta los tests manualmente para debugging."""
    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    session = Session(engine)
    ai_service = AIService(session)
    
    test_instance = TestAIService()
    test_instance.test_ai_workflow(ai_service)
    test_instance.test_loco_keyword_detection(ai_service)
    test_instance.test_sensitivity_detection(ai_service)
    
    session.close()


if __name__ == "__main__":
    run_manual_tests() 