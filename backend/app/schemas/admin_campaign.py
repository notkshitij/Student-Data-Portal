import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from app.models.campaign import CampaignStatus


class AdminCampaignListResponse(BaseModel):
    """List view of a campaign for admins."""
    model_config = ConfigDict(from_attributes=True)

    campaign_id: uuid.UUID
    name: str
    status: CampaignStatus
    student_count: int
    field_count: int
    created_at: datetime
    updated_at: datetime


class AdminCampaignDetailResponse(BaseModel):
    """Detailed view of a campaign for admins."""
    model_config = ConfigDict(from_attributes=True)

    campaign_id: uuid.UUID
    name: str
    description: str | None
    status: CampaignStatus
    student_count: int
    field_count: int
    collect_field_count: int
    created_at: datetime
    updated_at: datetime


class GenericAdminResponse(BaseModel):
    message: str
