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


# --- Form Builder Schemas ---

from typing import List, Optional, Any
from app.schemas.form_validation import FieldValidationConfig

class AdminFormField(BaseModel):
    """Represents a single field's configuration in the form builder."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    field_name: str
    field_order: int
    requires_student_input: bool
    validation_config: Optional[FieldValidationConfig] = None


class AdminFormConfigResponse(BaseModel):
    """The complete form configuration for a campaign."""
    campaign_id: uuid.UUID
    fields: List[AdminFormField]


class AdminFormFieldUpdate(BaseModel):
    """Update payload for a single field's validation configuration."""
    id: uuid.UUID
    validation_config: FieldValidationConfig


class AdminFormConfigUpdateRequest(BaseModel):
    """Bulk update payload for the form builder."""
    fields: List[AdminFormFieldUpdate]

