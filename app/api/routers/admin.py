from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import verify_admin_key, get_idp_provider
from app.schemas.admin import TenantCreate, TenantResponse
from app.models import Tenant
from app.database import get_db
from app.core.auth.idp import IdPProvider
import uuid

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/tenants", response_model=TenantResponse, dependencies=[Depends(verify_admin_key)])
async def register_tenant(
    tenant_in: TenantCreate,
    db: AsyncSession = Depends(get_db),
    idp: IdPProvider = Depends(get_idp_provider)
):
    # 1. Generate Tenant ID
    tenant_id = str(uuid.uuid4())
    
    # 2. Create DB Record
    new_tenant = Tenant(
        id=tenant_id,
        name=tenant_in.name
    )
    db.add(new_tenant)
    
    # 3. Provision Keycloak Client
    try:
        # Using the injected provider
        client_creds = idp.create_tenant_client(tenant_id=tenant_id, tenant_name=tenant_in.name)
    except Exception as e:
        # If IdP provisioning fails, we shouldn't commit the DB record
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to provision IdP: {str(e)}")

    # 4. Commit DB
    try:
        await db.commit()
        await db.refresh(new_tenant)
    except Exception as e:
        await db.rollback()
        # TODO: Cleanup Keycloak client if DB commit fails? 
        raise HTTPException(status_code=500, detail="Failed to save tenant to database")

    return TenantResponse(
        id=new_tenant.id,
        name=new_tenant.name,
        created_at=new_tenant.created_at,
        client_id=client_creds["client_id"],
        client_secret=client_creds["client_secret"]
    )
