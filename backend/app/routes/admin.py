"""
Admin routes.
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from typing import List

from app.database.session import get_db
from app.models.user import User
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_student import CampaignStudent
from app.models.campaign_field import CampaignField
from app.models.imported_field_value import ImportedFieldValue
from app.models.audit_log import AuditLog
from app.services.auth import get_current_admin
from app.services.import_excel import process_excel_import, MAX_FILE_BYTES
from app.schemas.import_config import ImportResponse
from app.schemas.admin_campaign import (
    AdminCampaignListResponse,
    AdminCampaignDetailResponse,
    GenericAdminResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/import", response_model=ImportResponse)
def import_campaign(
    campaign_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Import an Excel workbook to create a new campaign with student records.

    The workbook must contain an ``Email ID*`` header column to identify
    student login accounts.  All other columns are treated as dynamic
    campaign fields.
    """
    # --- Filename check (defence-in-depth; content is also verified) ----
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xlsx files are supported",
        )

    # --- Read file bytes with size limit --------------------------------
    try:
        file_bytes = file.file.read(MAX_FILE_BYTES + 1)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read the uploaded file",
        )

    if len(file_bytes) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum allowed size of "
                   f"{MAX_FILE_BYTES // (1024 * 1024)} MB",
        )

    # --- Process --------------------------------------------------------
    try:
        with db.begin_nested():
            result = process_excel_import(
                db=db,
                file_bytes=file_bytes,
                original_filename=file.filename,
                campaign_name=campaign_name,
                admin_id=admin.id,
            )
        db.commit()
        return result
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during import",
        )


@router.get("/campaigns", response_model=List[AdminCampaignListResponse])
def list_campaigns(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all campaigns available to the admin."""
    # Admins can see all campaigns
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    
    responses = []
    for c in campaigns:
        responses.append(
            AdminCampaignListResponse(
                campaign_id=c.id,
                name=c.name,
                status=c.status,
                student_count=len(c.students),
                field_count=len(c.fields),
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return responses


@router.get("/campaigns/{campaign_id}", response_model=AdminCampaignDetailResponse)
def get_campaign_detail(
    campaign_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get campaign details for review before publishing."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    # Count collect fields
    # Just need to check the unique fields that require input
    # Because ImportedFieldValue is stored per student per field, we can just check 
    # the first student's records, or query distinct fields requiring input
    collect_field_count = (
        db.query(ImportedFieldValue.campaign_field_id)
        .join(CampaignField)
        .filter(CampaignField.campaign_id == campaign_id, ImportedFieldValue.requires_student_input == True)
        .distinct()
        .count()
    )

    return AdminCampaignDetailResponse(
        campaign_id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        student_count=len(campaign.students),
        field_count=len(campaign.fields),
        collect_field_count=collect_field_count,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.post("/campaigns/{campaign_id}/publish", response_model=GenericAdminResponse)
def publish_campaign(
    campaign_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Publish a draft campaign, making it visible to students."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status == CampaignStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="Campaign is already published")
        
    if campaign.status != CampaignStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"Cannot publish campaign in status {campaign.status}")

    # Validate campaign integrity
    student_count = db.query(CampaignStudent).filter(CampaignStudent.campaign_id == campaign_id).count()
    if student_count == 0:
        raise HTTPException(status_code=400, detail="Cannot publish campaign with no students")
        
    field_count = db.query(CampaignField).filter(CampaignField.campaign_id == campaign_id).count()
    if field_count == 0:
        raise HTTPException(status_code=400, detail="Cannot publish campaign with no dynamic fields")

    try:
        # We don't use begin_nested because we want this transaction to commit fully or rollback fully
        # Update status
        campaign.status = CampaignStatus.PUBLISHED
        
        # Create audit log
        audit = AuditLog(
            user_id=admin.id,
            action="campaign_published",
            entity_type="campaign",
            entity_id=str(campaign.id),
            details={"status_from": "DRAFT", "status_to": "PUBLISHED"}
        )
        db.add(audit)
        
        db.commit()
        return GenericAdminResponse(message="Campaign published successfully")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while publishing the campaign")
