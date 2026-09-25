"""
Student API schemas.
"""

import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict
from app.models.campaign import CampaignStatus
from app.models.campaign_student import SubmissionStatus


class StudentCampaignListResponse(BaseModel):
    """A campaign the student belongs to."""
    model_config = ConfigDict(from_attributes=True)

    campaign_id: uuid.UUID
    name: str
    campaign_status: CampaignStatus
    submission_status: SubmissionStatus
    created_at: datetime


class StudentCampaignFieldResponse(BaseModel):
    """A dynamic field and the student's value/requirement."""
    model_config = ConfigDict(from_attributes=True)

    field_id: uuid.UUID
    field_name: str
    field_order: int
    requires_student_input: bool
    value: str | None
    validation_config: dict | None = None


class StudentCampaignDetailResponse(BaseModel):
    """Detailed view of a campaign for a student."""
    model_config = ConfigDict(from_attributes=True)

    campaign_id: uuid.UUID
    name: str
    description: str | None
    campaign_status: CampaignStatus
    submission_status: SubmissionStatus
    fields: List[StudentCampaignFieldResponse]


class StudentResponseUpdate(BaseModel):
    field_id: uuid.UUID
    value: str | None


class StudentResponseUpdateRequest(BaseModel):
    responses: List[StudentResponseUpdate]

