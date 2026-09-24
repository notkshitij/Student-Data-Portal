"""
Tests for the Excel import functionality.
"""

import io
import pytest
from openpyxl import Workbook
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User, UserRole
from app.models.campaign import Campaign
from app.models.campaign_field import CampaignField
from app.models.campaign_student import CampaignStudent
from app.models.imported_field_value import ImportedFieldValue
from app.models.import_record import Import, ImportStatus
from app.models.audit_log import AuditLog
from app.services import auth

def create_excel_bytes(rows: list[list]) -> bytes:
    """Helper to create an in-memory Excel file from a list of rows."""
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()

def test_admin_can_import_valid_workbook(client, admin_user, db_session):
    # Authenticate as admin
    login_resp = client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "adminpass"},
    )
    assert login_resp.status_code == 200
    token = login_resp.cookies[auth.SESSION_COOKIE_NAME]
    
    # Create valid workbook
    rows = [
        ["Email", "Name", "Phone"],
        ["student1@test.com", "Alice", "[COLLECT]"],
        ["student2@test.com", "[COLLECT]", "1234567890"],
    ]
    file_bytes = create_excel_bytes(rows)
    
    response = client.post(
        "/api/admin/import",
        data={
            "campaign_name": "Test Campaign",
            "email_column": "Email"
        },
        files={"file": ("test.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        cookies={auth.SESSION_COOKIE_NAME: token}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["num_students"] == 2
    assert data["num_fields"] == 3
    assert data["num_collect_cells"] == 2
    assert data["status"] == "COMPLETED"
    
    # Verify Campaign
    campaign = db_session.query(Campaign).filter_by(id=data["campaign_id"]).first()
    assert campaign is not None
    assert campaign.name == "Test Campaign"
    
    # Verify Fields (order preserved)
    fields = db_session.query(CampaignField).filter_by(campaign_id=campaign.id).order_by(CampaignField.field_order).all()
    assert len(fields) == 3
    assert fields[0].field_name == "Email"
    assert fields[1].field_name == "Name"
    assert fields[2].field_name == "Phone"
    
    # Verify Students and Values
    s1 = db_session.query(User).filter_by(email="student1@test.com").first()
    assert s1 is not None
    assert s1.role == UserRole.STUDENT
    
    cs1 = db_session.query(CampaignStudent).filter_by(campaign_id=campaign.id, student_id=s1.id).first()
    
    # Check Alice's imported values (Phone should be COLLECT)
    vals1 = db_session.query(ImportedFieldValue).filter_by(campaign_student_id=cs1.id).all()
    val_map1 = {v.campaign_field.field_name: v for v in vals1}
    assert val_map1["Name"].imported_value == "Alice"
    assert val_map1["Name"].requires_student_input is False
    assert val_map1["Phone"].imported_value is None
    assert val_map1["Phone"].requires_student_input is True
    
    # Check Bob (student2)'s imported values (Name should be COLLECT)
    s2 = db_session.query(User).filter_by(email="student2@test.com").first()
    cs2 = db_session.query(CampaignStudent).filter_by(campaign_id=campaign.id, student_id=s2.id).first()
    vals2 = db_session.query(ImportedFieldValue).filter_by(campaign_student_id=cs2.id).all()
    val_map2 = {v.campaign_field.field_name: v for v in vals2}
    assert val_map2["Name"].imported_value is None
    assert val_map2["Name"].requires_student_input is True
    assert val_map2["Phone"].imported_value == "1234567890"
    assert val_map2["Phone"].requires_student_input is False

    # Check Import record
    import_rec = db_session.query(Import).filter_by(campaign_id=campaign.id).first()
    assert import_rec is not None
    assert import_rec.row_count == 2
    
    # Check Audit Log
    audit = db_session.query(AuditLog).filter_by(action="IMPORT_CAMPAIGN", entity_id=str(campaign.id)).first()
    assert audit is not None
    assert audit.user_id == admin_user.id


def test_student_cannot_import(client, student_user):
    login_resp = client.post(
        "/api/auth/login",
        json={"email": student_user.email, "password": "studentpass"},
    )
    token = login_resp.cookies[auth.SESSION_COOKIE_NAME]
    
    rows = [["Email"], ["test@test.com"]]
    file_bytes = create_excel_bytes(rows)
    
    response = client.post(
        "/api/admin/import",
        data={"campaign_name": "Test", "email_column": "Email"},
        files={"file": ("test.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        cookies={auth.SESSION_COOKIE_NAME: token}
    )
    
    assert response.status_code == 403


def test_duplicate_emails_handled_correctly(client, admin_user, db_session):
    login_resp = client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "adminpass"},
    )
    token = login_resp.cookies[auth.SESSION_COOKIE_NAME]
    
    # File with duplicate email
    rows = [
        ["Email", "Name"],
        ["dup@test.com", "First Entry"],
        ["dup@test.com", "Second Entry"], # Should be skipped
    ]
    file_bytes = create_excel_bytes(rows)
    
    response = client.post(
        "/api/admin/import",
        data={"campaign_name": "Dup Campaign", "email_column": "Email"},
        files={"file": ("test.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        cookies={auth.SESSION_COOKIE_NAME: token}
    )
    
    assert response.status_code == 200
    assert response.json()["num_students"] == 1
    
    campaign_id = response.json()["campaign_id"]
    students = db_session.query(CampaignStudent).filter_by(campaign_id=campaign_id).all()
    assert len(students) == 1


def test_missing_email_column(client, admin_user):
    login_resp = client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "adminpass"},
    )
    token = login_resp.cookies[auth.SESSION_COOKIE_NAME]
    
    rows = [["NotEmail", "Name"], ["test@test.com", "Alice"]]
    file_bytes = create_excel_bytes(rows)
    
    response = client.post(
        "/api/admin/import",
        data={"campaign_name": "Test", "email_column": "Email"},
        files={"file": ("test.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        cookies={auth.SESSION_COOKIE_NAME: token}
    )
    
    assert response.status_code == 400
    assert "not found in headers" in response.json()["detail"]


def test_invalid_workbook_fails_atomically(client, admin_user, db_session):
    login_resp = client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "adminpass"},
    )
    token = login_resp.cookies[auth.SESSION_COOKIE_NAME]
    
    # Send a non-Excel file but with .xlsx extension
    response = client.post(
        "/api/admin/import",
        data={"campaign_name": "Fail Campaign", "email_column": "Email"},
        files={"file": ("test.xlsx", b"not an excel file", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        cookies={auth.SESSION_COOKIE_NAME: token}
    )
    
    assert response.status_code == 400
    
    # Ensure no partial data is created
    campaign = db_session.query(Campaign).filter_by(name="Fail Campaign").first()
    assert campaign is None


def test_existing_users_are_reused(client, admin_user, student_user, db_session):
    login_resp = client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "adminpass"},
    )
    token = login_resp.cookies[auth.SESSION_COOKIE_NAME]
    
    initial_user_count = db_session.query(func.count(User.id)).scalar()
    
    rows = [
        ["Email", "Name"],
        [student_user.email, "Existing Student"],
        ["new_student@test.com", "New Student"],
    ]
    file_bytes = create_excel_bytes(rows)
    
    response = client.post(
        "/api/admin/import",
        data={"campaign_name": "Reuse Campaign", "email_column": "Email"},
        files={"file": ("test.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        cookies={auth.SESSION_COOKIE_NAME: token}
    )
    
    assert response.status_code == 200
    assert response.json()["num_students"] == 2
    
    # Should only create 1 new user
    final_user_count = db_session.query(func.count(User.id)).scalar()
    assert final_user_count == initial_user_count + 1
