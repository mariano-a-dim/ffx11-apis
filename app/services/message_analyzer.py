from typing import Dict, Any, List
import re


class MessageAnalyzer:
    def __init__(self, user_id: str = "U123456", user_name: str = "madim"):
        """
        Inicializa el analizador con el ID y nombre del usuario.
        Reemplaza U123456 con tu user ID real de Slack.
        """
        self.user_id = user_id
        self.user_name = user_name.lower()
        
        # Palabras clave que indican que el mensaje es directo para ti
        self.direct_keywords = [
            "madim",
            "madi",
            "cto",
            "técnico",
            "desarrollo",
            "sistema",
            "bug",
            "error",
            "problema",
            "ayuda",
            "urgente",
            "crítico"
        ]
        
        # Preguntas directas
        self.question_patterns = [
            r"\?$",  # Termina con ?
            r"¿.*\?",  # Pregunta en español
            r"puedes",  # "¿puedes hacer...?"
            r"podrías",  # "¿podrías...?"
            r"necesito",  # "necesito ayuda"
            r"ayuda",  # "ayuda con..."
        ]

    def is_direct_message(self, message: Dict[str, Any]) -> bool:
        """
        Determina si un mensaje es directo para el usuario.
        """
        text = message.get("text", "").lower()
        
        # 1. Menciona directamente al usuario
        if self.user_name in text or f"<@{self.user_id}>" in text:
            return True
            
        # 2. Contiene palabras clave directas
        if any(keyword in text for keyword in self.direct_keywords):
            return True
            
        # 3. Es una pregunta directa
        if any(re.search(pattern, text) for pattern in self.question_patterns):
            return True
            
        # 4. Es en un thread donde ya participaste
        if message.get("thread_ts"):
            return True
            
        return False

    def get_urgency_level(self, message: Dict[str, Any]) -> str:
        """
        Determina el nivel de urgencia del mensaje.
        """
        text = message.get("text", "").lower()
        
        # Urgencia alta
        if any(word in text for word in ["urgente", "crítico", "emergencia", "error", "caído", "roto"]):
            return "high"
            
        # Urgencia media
        if any(word in text for word in ["problema", "bug", "ayuda", "necesito"]):
            return "medium"
            
        # Urgencia baja
        return "low" 