from fastapi import FastAPI
from app.api.endpoints import router as api_router
from app.api.routers.admin import router as admin_router
from app.api.routers.health import router as health_router
from app.core.logging import setup_logging

# Initialize structured logging
setup_logging()

app = FastAPI(title="Audit API", version="1.0.0")

app.include_router(api_router, prefix="/v1")
app.include_router(admin_router)
app.include_router(health_router)
