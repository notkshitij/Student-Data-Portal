"""
Student API routes.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_student import CampaignStudent
from app.models.user import User
from app.schemas.student import (
    StudentCampaignDetailResponse,
    StudentCampaignFieldResponse,
    StudentCampaignListResponse,
)
from app.services.auth import get_current_student

router = APIRouter(prefix="/student", tags=["student"])


@router.get("/campaigns", response_model=List[StudentCampaignListResponse])
def get_campaigns(
    current_student: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """
    Return all available campaigns the student is enrolled in.
    DRAFT campaigns are excluded.
    """
    memberships = (
        db.query(CampaignStudent)
        .join(Campaign, CampaignStudent.campaign_id == Campaign.id)
        .filter(
            CampaignStudent.student_id == current_student.id,
            Campaign.status != CampaignStatus.DRAFT,
        )
        .all()
    )

    responses = []
    for membership in memberships:
        responses.append(
            StudentCampaignListResponse(
                campaign_id=membership.campaign.id,
                name=membership.campaign.name,
                campaign_status=membership.campaign.status,
                submission_status=membership.status,
                created_at=membership.campaign.created_at,
            )
        )
    return responses


@router.get("/campaigns/{campaign_id}", response_model=StudentCampaignDetailResponse)
def get_campaign_detail(
    campaign_id: uuid.UUID,
    current_student: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """
    Get the detailed dynamic fields for a specific campaign the student is enrolled in.
    """
    # Verify student is in campaign and campaign is not DRAFT
    membership = (
        db.query(CampaignStudent)
        .join(Campaign, CampaignStudent.campaign_id == Campaign.id)
        .filter(
            CampaignStudent.student_id == current_student.id,
            CampaignStudent.campaign_id == campaign_id,
            Campaign.status != CampaignStatus.DRAFT,
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found or not available",
        )

    campaign = membership.campaign

    # Build field list by mapping imported values
    fields_resp = []
    
    # We want to order by CampaignField.field_order. membership.campaign.fields is already ordered by relationship
    for field in campaign.fields:
        # Find the ImportedFieldValue for this field and this student
        # We can search through membership.imported_field_values
        imported_val_record = next(
            (val for val in membership.imported_field_values if val.campaign_field_id == field.id), 
            None
        )
        
        if not imported_val_record:
            continue
            
        value_to_return = None
        
        if imported_val_record.requires_student_input:
            # If the student provided a response, return that.
            # Never return the imported_value (which is [COLLECT])
            if imported_val_record.student_response:
                value_to_return = imported_val_record.student_response.response_value
            else:
                value_to_return = None
        else:
            value_to_return = imported_val_record.imported_value

        fields_resp.append(
            StudentCampaignFieldResponse(
                field_id=field.id,
                field_name=field.field_name,
                field_order=field.field_order,
                requires_student_input=imported_val_record.requires_student_input,
                value=value_to_return,
            )
        )

    return StudentCampaignDetailResponse(
        campaign_id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        campaign_status=campaign.status,
        submission_status=membership.status,
        fields=fields_resp,
    )
