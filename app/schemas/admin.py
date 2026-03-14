from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.schemas.common import ID_REGEX

class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class TenantResponse(BaseModel):
    id: str = Field(..., pattern=ID_REGEX)
    name: str = Field(..., min_length=1, max_length=255)
    created_at: datetime
    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1)

