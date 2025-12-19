import requests
import time
import os
from functools import lru_cache

# Keycloak settings (should match app config or be passed in)
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "audit-realm")

class TokenManager:
    def __init__(self, keycloak_url=None, realm=None):
        self.keycloak_url = keycloak_url or KEYCLOAK_URL
        self.realm = realm or KEYCLOAK_REALM
        self.token_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
        self._tokens = {}  # Cache tokens: client_id -> (token, expiry)

    def get_token(self, client_id, client_secret):
        """
        Get a valid access token. Reuse cached token if valid.
        """
        now = time.time()
        if client_id in self._tokens:
            token, expiry = self._tokens[client_id]
            if now < expiry - 30:  # Buffer of 30 seconds
                return token

        # Fetch new token
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        try:
            response = requests.post(self.token_url, data=payload)
            response.raise_for_status()
            data = response.json()
            access_token = data["access_token"]
            expires_in = data.get("expires_in", 300)
            
            self._tokens[client_id] = (access_token, now + expires_in)
            return access_token
        except Exception as e:
            print(f"Failed to get token for {client_id}: {e}")
            raise

# Global instance for simple reuse
token_manager = TokenManager()

def get_token(client_id, client_secret):
    return token_manager.get_token(client_id, client_secret)

