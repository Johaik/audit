from typing import Dict, Any, Optional
import uuid
from app.core.auth.idp import IdPProvider

class MockIdPProvider(IdPProvider):
    def __init__(self):
        self.tenants = {} # tenant_id -> client_data
        self.tokens = {}  # token -> payload

    def create_tenant_client(self, tenant_id: str, tenant_name: str) -> Dict[str, str]:
        client_id = f"client-{tenant_id}"
        client_secret = f"secret-{tenant_id}"
        self.tenants[tenant_id] = {
            "client_id": client_id,
            "client_secret": client_secret,
            "name": tenant_name
        }
        return {"client_id": client_id, "client_secret": client_secret}

    def validate_token(self, token: str) -> Dict[str, Any]:
        if token in self.tokens:
            return self.tokens[token]
        raise ValueError("Invalid token")

    def get_public_key(self) -> str:
        return "mock-public-key"
    
    # Helper for tests to mint tokens
    def mint_token(self, tenant_id: str) -> str:
        token = f"mock-token-{tenant_id}"
        self.tokens[token] = {
            "tid": tenant_id,
            "sub": "test-client",
            "azp": f"client-{tenant_id}",
            "scope": "email profile",
            "exp": 9999999999
        }
        return token
