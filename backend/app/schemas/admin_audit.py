import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    user_email: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    details: Optional[dict[str, Any]]
    created_at: datetime

class AuditLogPaginatedResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
