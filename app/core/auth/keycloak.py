from typing import Dict, Any
from keycloak import KeycloakAdmin, KeycloakOpenID
from app.config import settings
from app.core.auth.idp import IdPProvider
import jwt

class KeycloakProvider(IdPProvider):
    def __init__(self):
        self.server_url = settings.KEYCLOAK_URL
        self.realm_name = settings.KEYCLOAK_REALM
        self.admin_username = settings.KEYCLOAK_ADMIN_USER
        self.admin_password = settings.KEYCLOAK_ADMIN_PASSWORD
        
        # Admin client for provisioning
        self.keycloak_admin = KeycloakAdmin(
            server_url=self.server_url,
            username=self.admin_username,
            password=self.admin_password,
            realm_name=self.realm_name,
            user_realm_name="master",  # Admin user is in master realm
            verify=True
        )

        # OpenID client for public key fetching (and potentially token validation if we didn't use pyjwt locally)
        self.keycloak_openid = KeycloakOpenID(
            server_url=self.server_url,
            client_id="admin-cli", # Just to init, we primarily need the keys
            realm_name=self.realm_name,
            verify=True
        )

    def create_tenant_client(self, tenant_id: str, tenant_name: str) -> Dict[str, str]:
        """
        Creates a new client in Keycloak for the tenant.
        Configures a protocol mapper to inject 'tid' claim.
        """
        client_id = f"tenant-{tenant_id}"
        
        # 1. Create Client
        new_client = self.keycloak_admin.create_client(payload={
            "clientId": client_id,
            "name": tenant_name,
            "enabled": True,
            "clientAuthenticatorType": "client-secret",
            "protocol": "openid-connect",
            "serviceAccountsEnabled": True, # For machine-to-machine
            "standardFlowEnabled": False,   # No user login UI for this MVP
            "directAccessGrantsEnabled": False,
            "publicClient": False,
        })
        
        # The create_client method returns the UUID of the client created, or we need to fetch it
        # python-keycloak create_client returns the UUID in some versions, or void.
        # Let's safely fetch the client_uuid
        client_uuid = self.keycloak_admin.get_client_id(client_id)

        # 2. Add Protocol Mapper for 'tid'
        self.keycloak_admin.add_mapper_to_client(
            client_id=client_uuid,
            payload={
                "name": "tenant-id-mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-hardcoded-claim-mapper",
                "consentRequired": False,
                "config": {
                    "claim.name": "tid",
                    "claim.value": tenant_id,
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true"
                }
            }
        )

        # 3. Get Client Secret
        # regenerate_client_secret returns dict with 'value'
        secret_data = self.keycloak_admin.get_client_secrets(client_uuid)
        client_secret = secret_data.get('value')

        return {
            "client_id": client_id,
            "client_secret": client_secret
        }

    def get_public_key(self) -> str:
        """
        Fetches the public key from Keycloak realm.
        Formatted as PEM.
        """
        key_info = self.keycloak_openid.public_key()
        # Keycloak returns the raw b64 key, we need to wrap it in PEM headers
        return f"-----BEGIN PUBLIC KEY-----\n{key_info}\n-----END PUBLIC KEY-----"

    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validates JWT signature against Keycloak public key.
        """
        public_key = self.get_public_key()

        options = {
            "verify_signature": True,
            "verify_aud": True,
            "exp": True
        }

        decoded = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options=options,
            audience=settings.KEYCLOAK_AUDIENCE,
        )

        return decoded
