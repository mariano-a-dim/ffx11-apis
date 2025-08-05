import re
import httpx
from typing import Dict, Any, Optional, List
from sqlmodel import Session

from app.core.config import settings
from app.core.logging import LoggerMixin


class SlackUserService(LoggerMixin):
    """Servicio para manejar información de usuarios de Slack con cache en memoria."""
    
    def __init__(self, session: Session):
        self.session = session
        # Cache en memoria: {user_id: user_info}
        self._user_cache: Dict[str, Dict[str, Any]] = {}
        # Cache de usuarios no encontrados para evitar llamadas repetidas
        self._not_found_cache: set = set()
    
    async def get_user_info(self, user_id: str, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de un usuario de Slack usando cache en memoria.
        
        Args:
            user_id: ID del usuario de Slack (ej: U036PD91RR6)
            access_token: Token personal de Slack
            
        Returns:
            Diccionario con información del usuario o None si no se encuentra
        """
        # 1. Verificar cache en memoria primero
        if user_id in self._user_cache:
            self.logger.debug("User info found in memory cache", user_id=user_id)
            return self._user_cache[user_id]
        
        # 2. Verificar si ya sabemos que no existe
        if user_id in self._not_found_cache:
            self.logger.debug("User marked as not found in cache", user_id=user_id)
            return None
        
        # 3. Si no está en cache, obtener de la API de Slack
        if not access_token:
            self.logger.warning("No access token provided, cannot fetch user info from Slack", user_id=user_id)
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://slack.com/api/users.info",
                    params={"user": user_id},
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        user_info = data.get("user", {})
                        
                        # Cachear en memoria para acceso futuro
                        self._user_cache[user_id] = user_info
                        self.logger.info("User info cached in memory", 
                                       user_id=user_id, name=user_info.get("name"))
                        return user_info
                    else:
                        error_msg = data.get("error", "unknown")
                        self.logger.warning("Slack API error getting user info", 
                                          user_id=user_id, error=error_msg)
                        
                        # Si es un error de usuario no encontrado, cachear como no encontrado
                        if error_msg == "user_not_found":
                            self._not_found_cache.add(user_id)
                            self.logger.info("User marked as not found", user_id=user_id)
                else:
                    self.logger.error("HTTP error getting user info", 
                                    user_id=user_id, status_code=response.status_code)
                    
        except Exception as e:
            self.logger.error("Error getting user info from Slack", 
                            user_id=user_id, error=str(e))
        
        return None
    
    def extract_user_mentions(self, text: str) -> List[str]:
        """
        Extrae todas las menciones de usuario del texto.
        
        Args:
            text: Texto del mensaje
            
        Returns:
            Lista de IDs de usuario mencionados
        """
        # Patrón para menciones de usuario: <@U1234567890>
        mention_pattern = r'<@([A-Z0-9]+)>'
        mentions = re.findall(mention_pattern, text)
        return mentions
    
    def replace_user_mentions(self, text: str, user_info_map: Dict[str, str]) -> str:
        """
        Reemplaza las menciones de usuario con nombres reales.
        
        Args:
            text: Texto original del mensaje
            user_info_map: Mapa de user_id -> nombre_real
            
        Returns:
            Texto con menciones reemplazadas por nombres
        """
        def replace_mention(match):
            user_id = match.group(1)
            if user_id in user_info_map:
                return f"@{user_info_map[user_id]}"
            else:
                # Si no tenemos información del usuario, mantener la mención original
                return match.group(0)
        
        # Reemplazar menciones de usuario
        text = re.sub(r'<@([A-Z0-9]+)>', replace_mention, text)
        
        # También reemplazar menciones de canal si las hay
        text = re.sub(r'<#([A-Z0-9]+)\|([^>]+)>', r'#\2', text)
        
        return text
    
    async def process_message_text(self, text: str, access_token: str) -> str:
        """
        Procesa el texto de un mensaje reemplazando menciones con nombres reales.
        
        Args:
            text: Texto original del mensaje
            access_token: Token personal de Slack
            
        Returns:
            Texto procesado con nombres reales
        """
        if not text:
            return text
        
        # Extraer menciones de usuario
        user_mentions = self.extract_user_mentions(text)
        
        if not user_mentions:
            return text
        
        # Obtener información de todos los usuarios mencionados
        user_info_map = {}
        for user_id in user_mentions:
            user_info = await self.get_user_info(user_id, access_token)
            if user_info:
                # Usar first_name como prioridad, sino name (username), sino display_name, sino real_name
                display_name = (user_info.get("profile", {}).get("first_name") or 
                              user_info.get("name") or 
                              user_info.get("profile", {}).get("display_name") or 
                              user_info.get("profile", {}).get("real_name") or 
                              user_id)
                user_info_map[user_id] = display_name
        
        # Reemplazar menciones en el texto
        processed_text = self.replace_user_mentions(text, user_info_map)
        
        self.logger.info("Processed message text", 
                        original_mentions=user_mentions,
                        processed_mentions=list(user_info_map.values()),
                        text_length=len(processed_text))
        
        return processed_text
    
    def clear_cache(self) -> None:
        """Limpia el cache en memoria."""
        self._user_cache.clear()
        self._not_found_cache.clear()
        self.logger.info("Memory cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas del cache."""
        return {
            "cached_users": len(self._user_cache),
            "not_found_users": len(self._not_found_cache)
        } 