"""
Student API routes.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

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
                validation_config=field.validation_config if imported_val_record.requires_student_input else None
            )
        )

    return StudentCampaignDetailResponse(
        campaign_id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        campaign_status=campaign.status,
        submission_status=membership.status,
        submitted_at=membership.submissions[0].submitted_at if membership.submissions else None,
        fields=fields_resp,
    )

from app.schemas.student import StudentResponseUpdateRequest
from app.models.student_response import StudentResponse
from app.models.campaign_field import CampaignField
from app.models.imported_field_value import ImportedFieldValue
from app.schemas.form_validation import FieldValidationConfig, validate_field_value
from app.models.campaign_student import SubmissionStatus

@router.put("/campaigns/{campaign_id}/responses")
def update_responses(
    campaign_id: uuid.UUID,
    request: StudentResponseUpdateRequest,
    current_student: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """
    Save or update a student's responses for a specific campaign.
    """
    # Verify student is in campaign, campaign is not DRAFT, and not SUBMITTED
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
        
    if membership.campaign.status == CampaignStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign is closed and no longer accepts changes",
        )
        
    if membership.status == SubmissionStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign has already been submitted and cannot be modified",
        )

    # Get all imported values for this student in this campaign
    # (this inherently scopes to the correct campaign and correct student)
    imported_values = {
        iv.campaign_field_id: iv
        for iv in db.query(ImportedFieldValue).filter(
            ImportedFieldValue.campaign_student_id == membership.id
        ).all()
    }
    
    # Get all campaign fields to access validation config
    fields = {
        f.id: f for f in db.query(CampaignField).filter(CampaignField.campaign_id == campaign_id).all()
    }

    errors = {}
    valid_responses = []
    seen_fields = set()

    # Validate each response
    for resp in request.responses:
        field_id = resp.field_id
        value = resp.value
        
        if field_id in seen_fields:
            errors[str(field_id)] = "Duplicate field submission in the same request."
            continue
        seen_fields.add(field_id)
        
        if field_id not in fields:
            errors[str(field_id)] = "Field does not belong to this campaign."
            continue
            
        if field_id not in imported_values:
            errors[str(field_id)] = "Field is not assigned to this student."
            continue
            
        imported_val = imported_values[field_id]
        if not imported_val.requires_student_input:
            errors[str(field_id)] = "Field does not accept student input."
            continue
            
        field_model = fields[field_id]
        
        # Get config, default to text/not required if none
        vconfig_dict = field_model.validation_config or {"type": "text", "rules": {"required": False}}
        vconfig = FieldValidationConfig.model_validate(vconfig_dict)
        
        try:
            normalized_val = validate_field_value(value, vconfig)
            valid_responses.append((imported_val, normalized_val))
        except ValueError as e:
            errors[str(field_id)] = str(e)

    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"field_errors": errors},
        )

    # If all valid, persist
    try:
        with db.begin_nested():
            for imported_val, normalized_val in valid_responses:
                if imported_val.student_response:
                    if normalized_val is None:
                        # They cleared an optional field
                        db.delete(imported_val.student_response)
                    else:
                        imported_val.student_response.response_value = normalized_val
                else:
                    if normalized_val is not None:
                        sr = StudentResponse(
                            imported_field_value_id=imported_val.id,
                            response_value=normalized_val
                        )
                        db.add(sr)
        db.commit()
        return {"message": "Responses saved successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save responses")

from app.models.campaign_submission import CampaignSubmission
from app.models.audit_log import AuditLog

@router.post("/campaigns/{campaign_id}/submit")
def submit_campaign(
    campaign_id: uuid.UUID,
    current_student: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """
    Permanently lock a campaign submission.
    Validates that all required fields are provided before allowing submission.
    """
    # 1. Fetch membership
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
        
    if membership.campaign.status == CampaignStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign is closed and no longer accepts changes",
        )
        
    if membership.status == SubmissionStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign has already been submitted",
        )
        
    # 2. Load fields and configurations
    fields = {
        f.id: f for f in db.query(CampaignField).filter(CampaignField.campaign_id == campaign_id).all()
    }
    
    # 3. Load student's imported values (and their responses via relationship)
    imported_values = db.query(ImportedFieldValue).filter(
        ImportedFieldValue.campaign_student_id == membership.id
    ).all()
    
    # 4. Validate all responses
    errors = {}
    
    for iv in imported_values:
        if not iv.requires_student_input:
            continue
            
        field_model = fields.get(iv.campaign_field_id)
        if not field_model:
            continue
            
        vconfig_dict = field_model.validation_config or {"type": "text", "rules": {"required": False}}
        vconfig = FieldValidationConfig.model_validate(vconfig_dict)
        
        student_response = iv.student_response.response_value if iv.student_response else None
        
        try:
            # We strictly evaluate the existing DB value through the canonical validator
            validate_field_value(student_response, vconfig)
        except ValueError as e:
            errors[str(iv.campaign_field_id)] = str(e)
            
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"field_errors": errors},
        )
        
    # 5. Atomically commit the submission
    try:
        with db.begin_nested():
            # Update membership status
            membership.status = SubmissionStatus.SUBMITTED
            
            # Create CampaignSubmission record
            submission = CampaignSubmission(
                campaign_student_id=membership.id
            )
            db.add(submission)
            
            # Create Audit Log
            audit = AuditLog(
                user_id=current_student.id,
                action="student_submission",
                entity_type="campaign_student",
                entity_id=str(membership.id),
                details={"campaign_id": str(campaign_id)}
            )
            db.add(audit)
            
        db.commit()
        return {"message": "Campaign submitted successfully"}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign has already been submitted",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to submit campaign")

