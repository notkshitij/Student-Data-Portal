"""
Admin routes.
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.services.auth import get_current_admin
from app.services.import_excel import process_excel_import
from app.schemas.import_config import ImportResponse

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/import", response_model=ImportResponse)
def import_campaign(
    campaign_name: str = Form(...),
    email_column: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Import an Excel file to create a new campaign and populate student records.
    """
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xlsx files are supported"
        )
        
    try:
        file_bytes = file.file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read file: {str(e)}"
        )
        
    try:
        with db.begin_nested():
            result = process_excel_import(
                db=db,
                file_bytes=file_bytes,
                original_filename=file.filename,
                campaign_name=campaign_name,
                email_column=email_column,
                admin_id=admin.id
            )
        db.commit()
        return result
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        # Ensure we log the unexpected error in real scenarios
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during import: {str(e)}"
        )
