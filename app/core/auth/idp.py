from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IdPProvider(ABC):
    """
    Abstract interface for Identity Provider operations.
    Decouples the application from specific IdP implementations (Keycloak, Auth0, etc).
    """

    @abstractmethod
    def create_tenant_client(self, tenant_id: str, tenant_name: str) -> Dict[str, str]:
        """
        Provision a new client/application in the IdP for a tenant.
        
        Args:
            tenant_id: Unique identifier for the tenant (internal)
            tenant_name: Display name for the tenant
            
        Returns:
            Dict containing credentials (client_id, client_secret)
        """
        pass

    @abstractmethod
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a JWT token and return its payload.
        
        Args:
            token: The raw JWT string
            
        Returns:
            Dict containing the token claims/payload
            
        Raises:
            ValueError: If token is invalid or expired
        """
        pass
    
    @abstractmethod
    def get_public_key(self) -> str:
        """
        Retrieve the public key for verifying tokens.
        """
        pass

