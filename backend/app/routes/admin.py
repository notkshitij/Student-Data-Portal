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
    AdminFormConfigResponse,
    AdminFormConfigUpdateRequest,
    AdminFormField
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

@router.get("/campaigns/{campaign_id}/form", response_model=AdminFormConfigResponse)
def get_campaign_form_config(
    campaign_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get the form validation configuration for all fields in a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    # We need to know which fields require student input.
    # A field requires student input if any ImportedFieldValue for it has requires_student_input=True.
    # Assuming all imported values for a collect field have requires_student_input=True.
    collect_fields_subq = (
        db.query(ImportedFieldValue.campaign_field_id)
        .filter(ImportedFieldValue.requires_student_input == True)
        .distinct()
    ).subquery()
    
    # Actually, the user requirements state:
    # `requires_student_input` comes from the Excel `[COLLECT]` marker.
    # Let's get all fields and check if they are in collect_fields_subq
    fields = db.query(CampaignField).filter(CampaignField.campaign_id == campaign_id).order_by(CampaignField.field_order).all()
    
    collect_field_ids = {
        row[0] for row in db.query(collect_fields_subq.c.campaign_field_id).all()
    }
    
    response_fields = []
    for f in fields:
        # Default config if null
        vconfig = f.validation_config
        if not vconfig and f.id in collect_field_ids:
            vconfig = {"type": "text", "rules": {"required": False}}
            
        response_fields.append(
            AdminFormField(
                id=f.id,
                field_name=f.field_name,
                field_order=f.field_order,
                requires_student_input=f.id in collect_field_ids,
                validation_config=vconfig
            )
        )
        
    return AdminFormConfigResponse(
        campaign_id=campaign_id,
        fields=response_fields
    )


@router.put("/campaigns/{campaign_id}/form", response_model=GenericAdminResponse)
def update_campaign_form_config(
    campaign_id: uuid.UUID,
    request: AdminFormConfigUpdateRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update field ordering (all fields) and validation config (collectable fields only)."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    # Only allow edits in DRAFT or CLOSED state
    if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.CLOSED}:
        raise HTTPException(
            status_code=400,
            detail="Form configuration can only be modified for DRAFT or CLOSED campaigns"
        )
        
    # Fetch all fields for this campaign
    all_campaign_fields = db.query(CampaignField).filter(CampaignField.campaign_id == campaign_id).all()
    fields_by_id = {f.id: f for f in all_campaign_fields}
    
    # Identify collect fields
    collect_fields_subq = (
        db.query(ImportedFieldValue.campaign_field_id)
        .filter(ImportedFieldValue.requires_student_input == True)
        .distinct()
    ).subquery()
    
    collect_field_ids = {
        row[0] for row in db.query(collect_fields_subq.c.campaign_field_id).all()
    }
    
    orders_updated = 0
    configs_updated = 0
    
    try:
        with db.begin_nested():
            # --- 1. Process field ordering (ALL fields) ---
            if request.field_orders:
                submitted_ids = set()
                submitted_orders = set()
                
                for order_update in request.field_orders:
                    fid = order_update.id
                    
                    if fid not in fields_by_id:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Field {fid} does not belong to this campaign"
                        )
                    
                    if fid in submitted_ids:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Duplicate field ID in ordering: {fid}"
                        )
                    submitted_ids.add(fid)
                    
                    if order_update.field_order in submitted_orders:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Duplicate field_order position: {order_update.field_order}"
                        )
                    submitted_orders.add(order_update.field_order)
                
                # Verify ALL campaign fields are present
                if submitted_ids != set(fields_by_id.keys()):
                    missing = set(fields_by_id.keys()) - submitted_ids
                    extra = submitted_ids - set(fields_by_id.keys())
                    detail_parts = []
                    if missing:
                        detail_parts.append(f"Missing fields: {[str(x) for x in missing]}")
                    if extra:
                        detail_parts.append(f"Extra fields: {[str(x) for x in extra]}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Ordering must include all campaign fields. {'; '.join(detail_parts)}"
                    )
                
                # Apply ordering
                for order_update in request.field_orders:
                    field = fields_by_id[order_update.id]
                    if field.field_order != order_update.field_order:
                        field.field_order = order_update.field_order
                        orders_updated += 1
            
            # --- 2. Process validation config (collectable fields only) ---
            for update_field in request.fields:
                field_id = update_field.id
                if field_id not in fields_by_id:
                    raise HTTPException(status_code=400, detail=f"Field {field_id} does not belong to this campaign")
                if field_id not in collect_field_ids:
                    raise HTTPException(status_code=400, detail=f"Field {field_id} is not a collect field and cannot be configured")
                    
                field = fields_by_id[field_id]
                field.validation_config = update_field.validation_config.model_dump()
                configs_updated += 1
                
        # Create audit log
        audit = AuditLog(
            user_id=admin.id,
            action="form_config_updated",
            entity_type="campaign",
            entity_id=str(campaign_id),
            details={"orders_updated": orders_updated, "configs_updated": configs_updated}
        )
        db.add(audit)
        
        db.commit()
        return GenericAdminResponse(message="Form configuration updated successfully")
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update form configuration")

from app.schemas.admin_campaign import (
    AdminCampaignProgressResponse,
    AdminStudentListResponse,
    AdminStudentListPaginatedResponse,
    AdminStudentDetailResponse,
    AdminStudentDetailField
)
from app.models.campaign_student import CampaignStudent, SubmissionStatus
from typing import Optional

@router.get("/campaigns/{campaign_id}/progress", response_model=AdminCampaignProgressResponse)
def get_campaign_progress(
    campaign_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Efficient counts
    total_students = db.query(CampaignStudent).filter(CampaignStudent.campaign_id == campaign_id).count()
    submitted_students = db.query(CampaignStudent).filter(
        CampaignStudent.campaign_id == campaign_id,
        CampaignStudent.status == SubmissionStatus.SUBMITTED
    ).count()
    
    pending_students = total_students - submitted_students
    
    submission_percentage = (submitted_students / total_students * 100) if total_students > 0 else 0.0
    
    return AdminCampaignProgressResponse(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        campaign_status=campaign.status,
        total_students=total_students,
        pending_students=pending_students,
        submitted_students=submitted_students,
        submission_percentage=submission_percentage
    )


@router.get("/campaigns/{campaign_id}/students", response_model=AdminStudentListPaginatedResponse)
def get_campaign_students(
    campaign_id: uuid.UUID,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = db.query(CampaignStudent).filter(CampaignStudent.campaign_id == campaign_id)
    
    if status and status.upper() != "ALL":
        if status.upper() not in [SubmissionStatus.PENDING, SubmissionStatus.SUBMITTED]:
            raise HTTPException(status_code=400, detail="Invalid status filter")
        query = query.filter(CampaignStudent.status == status.upper())
        
    total = query.count()
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Load students efficiently with eager loading for user and submissions
    from sqlalchemy.orm import joinedload
    memberships = query.options(
        joinedload(CampaignStudent.student),
        joinedload(CampaignStudent.submissions)
    ).limit(page_size).offset(offset).all()
    
    items = []
    for m in memberships:
        submitted_at = m.submissions[0].submitted_at if m.submissions else None
        items.append(AdminStudentListResponse(
            student_id=m.student.id,
            email=m.student.email,
            status=m.status,
            submitted_at=submitted_at
        ))
        
    return AdminStudentListPaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/campaigns/{campaign_id}/students/{student_id}", response_model=AdminStudentDetailResponse)
def get_campaign_student_detail(
    campaign_id: uuid.UUID,
    student_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    # Verify enrollment
    membership = db.query(CampaignStudent).filter(
        CampaignStudent.campaign_id == campaign_id,
        CampaignStudent.student_id == student_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=404, detail="Student is not enrolled in this campaign")
        
    campaign = membership.campaign
    student = membership.student
    submitted_at = membership.submissions[0].submitted_at if membership.submissions else None
    
    fields_resp = []
    
    for field in campaign.fields:
        # Find the ImportedFieldValue for this field and this student
        imported_val_record = next(
            (val for val in membership.imported_field_values if val.campaign_field_id == field.id), 
            None
        )
        
        if not imported_val_record:
            continue
            
        student_response_val = None
        if imported_val_record.student_response:
            student_response_val = imported_val_record.student_response.response_value
            
        fields_resp.append(AdminStudentDetailField(
            field_id=field.id,
            field_name=field.field_name,
            field_order=field.field_order,
            requires_student_input=imported_val_record.requires_student_input,
            imported_value=imported_val_record.imported_value,
            student_response=student_response_val,
            validation_config=field.validation_config
        ))
        
    return AdminStudentDetailResponse(
        student_id=student.id,
        email=student.email,
        campaign_id=campaign.id,
        status=membership.status,
        submitted_at=submitted_at,
        fields=fields_resp
    )

import csv
import io
import re
from fastapi.responses import StreamingResponse

def _sanitize_csv_value(val: str | None) -> str:
    """Sanitize CSV value to prevent formula injection."""
    if val is None:
        return ""
    val = str(val)
    if val and val[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + val
    return val

@router.get("/campaigns/{campaign_id}/export")
def export_campaign_data(
    campaign_id: uuid.UUID,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = db.query(CampaignStudent).filter(CampaignStudent.campaign_id == campaign_id)
    
    if status and status.upper() != "ALL":
        if status.upper() not in [SubmissionStatus.PENDING, SubmissionStatus.SUBMITTED]:
            raise HTTPException(status_code=400, detail="Invalid status filter")
        query = query.filter(CampaignStudent.status == status.upper())

    # Create audit log
    audit = AuditLog(
        user_id=current_admin.id,
        action="campaign_export",
        entity_type="campaign",
        entity_id=str(campaign.id),
        details={"status_filter": status or "ALL"}
    )
    db.add(audit)
    db.commit()

    fields = sorted(campaign.fields, key=lambda f: f.field_order)
    headers = [f.field_name for f in fields] + ["Submission Status", "Submitted At"]

    def iter_csv():
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Batch loading to avoid memory explosion, though typically campaigns are < 10k students
        # We can just iterate over query
        # Since we need ImportedFieldValue and StudentResponse, eager loading helps
        from sqlalchemy.orm import selectinload, joinedload
        memberships = query.options(
            joinedload(CampaignStudent.student),
            selectinload(CampaignStudent.submissions),
            selectinload(CampaignStudent.imported_field_values).joinedload(ImportedFieldValue.student_response)
        ).yield_per(100)

        for m in memberships:
            row = []
            
            # Map imported values by field id for fast lookup
            iv_map = {iv.campaign_field_id: iv for iv in m.imported_field_values}

            for field in fields:
                iv = iv_map.get(field.id)
                val = ""
                if iv:
                    if not iv.requires_student_input:
                        val = iv.imported_value
                    else:
                        if iv.student_response:
                            val = iv.student_response.response_value
                        else:
                            val = ""
                row.append(_sanitize_csv_value(val))
            
            row.append(_sanitize_csv_value(str(m.status)))
            submitted_at = m.submissions[0].submitted_at if m.submissions else None
            row.append(_sanitize_csv_value(submitted_at.isoformat() if submitted_at else ""))
            
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    # Sanitize campaign name for filename
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', campaign.name)
    filename = f"{safe_name}-verified-data.csv"

    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

@router.post("/campaigns/{campaign_id}/close", response_model=GenericAdminResponse)
def close_campaign(
    campaign_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).with_for_update().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    if campaign.status == CampaignStatus.CLOSED:
        return GenericAdminResponse(message="Campaign is already closed")
        
    if campaign.status != CampaignStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Only PUBLISHED campaigns can be closed")

    try:
        # Update status
        campaign.status = CampaignStatus.CLOSED
        
        # Create audit log
        audit = AuditLog(
            user_id=current_admin.id,
            action="campaign_closed",
            entity_type="campaign",
            entity_id=str(campaign.id),
            details={"status_from": "PUBLISHED", "status_to": "CLOSED"}
        )
        db.add(audit)
        
        db.commit()
        return GenericAdminResponse(message="Campaign closed successfully")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while closing the campaign")


@router.post("/campaigns/{campaign_id}/reopen", response_model=GenericAdminResponse)
def reopen_campaign(
    campaign_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).with_for_update().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    if campaign.status == CampaignStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Campaign is already published")
        
    if campaign.status == CampaignStatus.DRAFT:
        raise HTTPException(status_code=400, detail="DRAFT campaigns cannot be reopened. Publish them instead.")

    try:
        # Update status
        campaign.status = CampaignStatus.PUBLISHED
        
        # Create audit log
        audit = AuditLog(
            user_id=current_admin.id,
            action="campaign_reopened",
            entity_type="campaign",
            entity_id=str(campaign.id),
            details={"status_from": "CLOSED", "status_to": "PUBLISHED"}
        )
        db.add(audit)
        
        db.commit()
        return GenericAdminResponse(message="Campaign reopened successfully")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while reopening the campaign")

from datetime import datetime
from typing import Optional, List
from sqlalchemy import desc
from app.models.audit_log import AuditLog
from app.schemas.admin_audit import AuditLogPaginatedResponse, AuditLogResponse

@router.get("/audit-logs", response_model=AuditLogPaginatedResponse)
def get_audit_logs(
    page: int = 1,
    page_size: int = 50,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    campaign_id: Optional[uuid.UUID] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Get audit logs with optional filtering and pagination.
    Admin-only access.
    """
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="Page size must be between 1 and 100")

    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
        
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
        
    if campaign_id:
        query = query.filter(
            AuditLog.entity_type == "campaign",
            AuditLog.entity_id == str(campaign_id)
        )
        
    if from_date:
        query = query.filter(AuditLog.created_at >= from_date)
        
    if to_date:
        query = query.filter(AuditLog.created_at <= to_date)
        
    total = query.count()
    
    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    logs = query.all()
    
    # We need to map user_email if available
    # Avoid N+1 by collecting user ids and fetching them
    user_ids = {log.user_id for log in logs if log.user_id}
    users = {u.id: u.email for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    
    items = []
    for log in logs:
        # Sanitize details if necessary. Currently no sensitive data is known to be in details,
        # but we should ensure no session tokens or passwords are in details.
        sanitized_details = log.details.copy() if log.details else None
        
        # In case some existing action contains sensitive keys, we filter them out
        if sanitized_details:
            sensitive_keys = ["password", "token", "secret", "google_subject_id", "session"]
            for k in sensitive_keys:
                if k in sanitized_details:
                    del sanitized_details[k]

        items.append(
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                user_email=users.get(log.user_id),
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                details=sanitized_details,
                created_at=log.created_at
            )
        )
        
    total_pages = (total + page_size - 1) // page_size

    return AuditLogPaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
