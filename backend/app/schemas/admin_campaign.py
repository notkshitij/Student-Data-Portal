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
    """Update payload for a single field's validation configuration and order."""
    id: uuid.UUID
    field_order: Optional[int] = None
    validation_config: FieldValidationConfig


class AdminFormConfigUpdateRequest(BaseModel):
    """Bulk update payload for the form builder."""
    fields: List[AdminFormFieldUpdate]


# --- Campaign Progress and Submissions ---

from app.models.campaign_student import SubmissionStatus

class AdminCampaignProgressResponse(BaseModel):
    campaign_id: uuid.UUID
    campaign_name: str
    campaign_status: CampaignStatus
    total_students: int
    pending_students: int
    submitted_students: int
    submission_percentage: float


class AdminStudentListResponse(BaseModel):
    student_id: uuid.UUID
    email: str
    status: SubmissionStatus
    submitted_at: datetime | None


class AdminStudentListPaginatedResponse(BaseModel):
    items: List[AdminStudentListResponse]
    total: int
    page: int
    page_size: int


class AdminStudentDetailField(BaseModel):
    field_id: uuid.UUID
    field_name: str
    field_order: int
    requires_student_input: bool
    imported_value: str | None
    student_response: str | None
    validation_config: FieldValidationConfig | None


class AdminStudentDetailResponse(BaseModel):
    student_id: uuid.UUID
    email: str
    campaign_id: uuid.UUID
    status: SubmissionStatus
    submitted_at: datetime | None
    fields: List[AdminStudentDetailField]
