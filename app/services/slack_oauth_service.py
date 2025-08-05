import httpx
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.exceptions import SlackException
from app.core.logging import LoggerMixin


class SlackOAuthService(LoggerMixin):
    """Servicio para manejar OAuth de Slack."""
    
    def __init__(self):
        self.client_id = settings.SLACK_CLIENT_ID
        self.client_secret = settings.SLACK_CLIENT_SECRET
        self.redirect_uri = settings.SLACK_REDIRECT_URI
        self.logger.info("SlackOAuthService initialized")
        
    def validate_configuration(self) -> bool:
        """
        Valida que la configuración de Slack esté completa.
        """
        return all([
            self.client_id,
            self.client_secret,
            self.redirect_uri
        ])
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Intercambia el código de autorización por un token de acceso.
        """
        self.logger.info("Starting OAuth token exchange", has_code=bool(code))
        
        if not self.validate_configuration():
            self.logger.error("Slack configuration validation failed")
            raise SlackException("Slack configuration not properly set")
            
        if not code:
            self.logger.error("Missing authorization code")
            raise SlackException("Missing authorization code")
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/oauth.v2.access",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
            data = response.json()
            
            if not data.get("ok"):
                error = data.get("error", "Unknown error")
                self.logger.error("Slack OAuth failed", error=error, response_data=data)
                raise SlackException(f"Slack OAuth failed: {error}")
            
            self.logger.info("OAuth token exchange successful")
            return data
            
        except httpx.RequestError as e:
            self.logger.error("Network error during OAuth", error=str(e))
            raise SlackException(f"Network error during OAuth: {str(e)}")
        except Exception as e:
            self.logger.error("Unexpected error during OAuth", error=str(e), exc_info=True)
            raise SlackException(f"Unexpected error during OAuth: {str(e)}")
    
    def get_access_token(self, oauth_data: Dict[str, Any]) -> Optional[str]:
        """
        Extrae el token de acceso del resultado de OAuth.
        """
        return oauth_data.get("authed_user", {}).get("access_token")
    
    def get_team_info(self, oauth_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extrae información del equipo del resultado de OAuth.
        """
        return oauth_data.get("team")
    
    def get_user_info(self, oauth_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extrae información del usuario del resultado de OAuth.
        """
        return oauth_data.get("authed_user") 