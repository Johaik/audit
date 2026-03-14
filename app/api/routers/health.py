from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import time
import asyncio
import logging
from typing import Dict, Any

from app.api.deps import get_db, get_idp_provider
from app.core.auth.idp import IdPProvider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["observability"])

async def check_postgres(db: AsyncSession) -> Dict[str, Any]:
    start_time = time.time()
    try:
        await db.execute(text("SELECT 1"))
        latency = (time.time() - start_time) * 1000
        return {"status": "up", "latency_ms": round(latency, 2)}
    except Exception as e:
        logger.error(f"Postgres health check failed: {e}")
        return {"status": "down", "error": str(e)}

async def check_keycloak(idp: IdPProvider) -> Dict[str, Any]:
    start_time = time.time()
    try:
        from fastapi.concurrency import run_in_threadpool
        # Run the IdP's health check in a threadpool if it's potentially blocking
        res = await run_in_threadpool(idp.check_health)
        latency = (time.time() - start_time) * 1000
        if res["status"] == "up":
            res["latency_ms"] = round(latency, 2)
        return res
    except Exception as e:
        logger.error(f"Keycloak health check failed: {e}")
        return {"status": "down", "error": str(e)}

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    idp: IdPProvider = Depends(get_idp_provider)
):
    postgres_task = check_postgres(db)
    keycloak_task = check_keycloak(idp)
    
    postgres_res, keycloak_res = await asyncio.gather(postgres_task, keycloak_task)
    
    overall_status = "ok"
    if postgres_res["status"] != "up" or keycloak_res["status"] != "up":
        overall_status = "error"
        
    return {
        "status": overall_status,
        "timestamp": time.time(),
        "components": {
            "postgres": postgres_res,
            "keycloak": keycloak_res
        }
    }
