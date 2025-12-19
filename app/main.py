from fastapi import FastAPI
from app.api.endpoints import router as api_router

app = FastAPI(title="Audit API", version="1.0.0")

app.include_router(api_router, prefix="/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

