from fastapi import FastAPI
from app.api.endpoints import router as api_router
from app.api.routers.admin import router as admin_router
from app.api.routers.health import router as health_router
from app.core.logging import setup_logging, get_logger
from app.core.tracing import setup_tracing
from app.database import engine

# Initialize structured logging
setup_logging()

app = FastAPI(title="Audit API", version="1.0.0")

# Initialize distributed tracing
setup_tracing(app, engine)

from opentelemetry import trace
from fastapi import Request

@app.middleware("http")
async def add_trace_id_header(request: Request, call_next):
    span = trace.get_current_span()
    trace_id = format(span.get_span_context().trace_id, "032x")
    response = await call_next(request)
    if trace_id != "00000000000000000000000000000000":
        response.headers["X-Trace-Id"] = trace_id
    return response

app.include_router(api_router, prefix="/v1")
app.include_router(admin_router)
app.include_router(health_router)
