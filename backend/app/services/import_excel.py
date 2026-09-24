"""
Service for importing Excel data.
"""

import io
from pydantic import EmailStr, ValidationError
from pydantic import TypeAdapter
from openpyxl import load_workbook
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uuid

from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_field import CampaignField
from app.models.user import User, UserRole
from app.models.campaign_student import CampaignStudent, SubmissionStatus
from app.models.imported_field_value import ImportedFieldValue
from app.models.import_record import Import, ImportStatus
from app.models.audit_log import AuditLog
from app.services.auth import hash_password

email_adapter = TypeAdapter(EmailStr)

def process_excel_import(
    db: Session,
    file_bytes: bytes,
    original_filename: str,
    campaign_name: str,
    email_column: str,
    admin_id: uuid.UUID
) -> dict:
    """
    Processes an Excel file, creating the campaign, fields, students, and values.
    Raises ValueError on validation failure.
    """
    try:
        wb = load_workbook(filename=io.BytesIO(file_bytes), read_only=True, data_only=True)
        sheet = wb.active
    except Exception as e:
        raise ValueError(f"Invalid Excel file: {str(e)}")

    rows = iter(sheet.rows)
    try:
        header_row = next(rows)
    except StopIteration:
        raise ValueError("Workbook is empty")
        
    headers = [str(cell.value).strip() if cell.value is not None else f"Column_{i}" for i, cell in enumerate(header_row)]
    
    if not headers:
        raise ValueError("No headers found in the first row")
        
    # Case-insensitive column matching for email
    email_col_idx = -1
    for i, h in enumerate(headers):
        if h.lower() == email_column.lower():
            email_col_idx = i
            break
            
    if email_col_idx == -1:
        raise ValueError(f"Required email column '{email_column}' not found in headers: {headers}")

    # Create Campaign
    campaign = Campaign(
        name=campaign_name,
        status=CampaignStatus.DRAFT,
        created_by_id=admin_id
    )
    db.add(campaign)
    db.flush()

    # Create Import record
    import_record = Import(
        campaign_id=campaign.id,
        uploaded_by_id=admin_id,
        original_filename=original_filename,
        status=ImportStatus.PROCESSING
    )
    db.add(import_record)
    db.flush()
    
    # Create Campaign Fields
    campaign_fields = []
    for order, header in enumerate(headers):
        field = CampaignField(
            campaign_id=campaign.id,
            field_name=header,
            field_order=order
        )
        db.add(field)
        campaign_fields.append(field)
    
    db.flush()

    num_students = 0
    num_collect_cells = 0
    processed_emails = set()
    
    # Process rows
    for row in rows:
        row_values = [cell.value for cell in row]
        # Skip completely empty rows
        if all(v is None or str(v).strip() == "" for v in row_values):
            continue
            
        raw_email = row_values[email_col_idx]
        if not raw_email:
            continue # Skip row if email is missing
            
        # Normalize and validate email
        try:
            email = email_adapter.validate_python(raw_email).lower()
        except ValidationError:
            # Skip invalid emails to continue processing valid ones
            # (or we could fail the whole import, but typical behavior is to skip or log)
            continue
            
        if email in processed_emails:
            continue # Skip duplicate student within this file
            
        processed_emails.add(email)
        
        # Get or create User
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Generate random password for now
            temp_pass = str(uuid.uuid4())
            user = User(
                email=email,
                role=UserRole.STUDENT,
                password_hash=hash_password(temp_pass)
            )
            db.add(user)
            db.flush()
            
        # Create CampaignStudent membership
        cs = CampaignStudent(
            campaign_id=campaign.id,
            student_id=user.id
        )
        db.add(cs)
        db.flush()
        num_students += 1
        
        # Create ImportedFieldValues
        for field, value in zip(campaign_fields, row_values):
            requires_input = False
            str_val = str(value).strip() if value is not None else ""
            
            if str_val.lower() == "[collect]":
                requires_input = True
                num_collect_cells += 1
                stored_value = None
            else:
                stored_value = str(value) if value is not None else None
                
            ifv = ImportedFieldValue(
                campaign_student_id=cs.id,
                campaign_field_id=field.id,
                imported_value=stored_value,
                requires_student_input=requires_input
            )
            db.add(ifv)

    from datetime import datetime, timezone
    import_record.status = ImportStatus.COMPLETED
    import_record.row_count = num_students
    import_record.completed_at = datetime.now(timezone.utc)
    
    # Audit Log
    audit = AuditLog(
        user_id=admin_id,
        action="IMPORT_CAMPAIGN",
        entity_type="Campaign",
        entity_id=str(campaign.id),
        details={
            "filename": original_filename,
            "students_imported": num_students,
            "fields_count": len(campaign_fields)
        }
    )
    db.add(audit)
    
    return {
        "campaign_id": campaign.id,
        "num_students": num_students,
        "num_fields": len(campaign_fields),
        "num_collect_cells": num_collect_cells,
        "status": import_record.status.value
    }
