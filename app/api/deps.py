from fastapi import Header, HTTPException, Security, Depends, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any

from app.config import settings
from app.database import get_db
from app.core.auth.keycloak import KeycloakProvider
from app.core.auth.idp import IdPProvider

# Admin Security
admin_api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)

async def verify_admin_key(api_key: str = Security(admin_api_key_header)):
    if not api_key or api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid Admin Key")
    return api_key

# Data Plane Security
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=True)

_idp_provider = None

def get_idp_provider():
    global _idp_provider
    if not _idp_provider:
        _idp_provider = KeycloakProvider()
    return _idp_provider

async def verify_jwt(
    token: str = Depends(oauth2_scheme),
    idp: IdPProvider = Depends(get_idp_provider)
) -> Dict[str, Any]:
    try:
        # In a real app, we should cache the public key
        payload = idp.validate_token(token)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_tenant_id(
    token_payload: Dict[str, Any] = Depends(verify_jwt)
) -> str:
    tenant_id = token_payload.get("tid")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Token missing tenant context")
    return tenant_id

async def get_db_with_context(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    # Set RLS context
    try:
        # Use set_config for safer variable setting
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"), 
            {"tenant_id": tenant_id}
        )
    except Exception as e:
        print(f"DEBUG: SET LOCAL FAILED: {e}") # Print to stdout for test debugging
        raise HTTPException(status_code=500, detail="Failed to set tenant context")
    
    yield db
