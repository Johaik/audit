from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TenantCreate(BaseModel):
    name: str

class TenantResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    client_id: str
    client_secret: str

