import pytest
import uuid
import io
from app.models.campaign import Campaign, CampaignStatus

from openpyxl import Workbook

def create_valid_excel_bytes():
    wb = Workbook()
    ws = wb.active
    ws.append(["Email ID*", "Name", "Phone"])
    ws.append(["student1@poornima.edu.in", "Student One", "[COLLECT]"])
    ws.append(["student2@poornima.org", "Student Two", "9876543210"])
    
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()

def _login_as_admin(client, mock_google_auth):
    response = client.post("/api/auth/login", json={"code": "valid_code_admin"})
    return response.cookies

def test_campaign_create_and_delete(client, mock_google_auth, db_session, admin_user):
    cookies = _login_as_admin(client, mock_google_auth)
    # Create campaign
    response = client.post("/api/admin/campaigns", json={"name": "Test Campaign", "description": "Test"}, cookies=cookies)
    assert response.status_code == 200
    campaign_id = response.json()["campaign_id"]
    
    # Delete campaign
    response = client.delete(f"/api/admin/campaigns/{campaign_id}", cookies=cookies)
    assert response.status_code == 200
    
    # Verify deletion
    camp = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    assert camp is None

def test_excel_upload_and_replace(client, mock_google_auth, db_session, admin_user):
    cookies = _login_as_admin(client, mock_google_auth)
    # Create campaign
    response = client.post("/api/admin/campaigns", json={"name": "Test Campaign 2"}, cookies=cookies)
    assert response.status_code == 200
    campaign_id = response.json()["campaign_id"]
    
    # Upload Excel
    excel_bytes = create_valid_excel_bytes()
    response = client.post(
        f"/api/admin/campaigns/{campaign_id}/import",
        files={"file": ("test.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        cookies=cookies
    )
    assert response.status_code == 200
    assert response.json()["num_students"] == 2
    
    # Test download
    response = client.get(f"/api/admin/campaigns/{campaign_id}/excel", cookies=cookies)
    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="test.xlsx"'
    
    # Publish campaign
    response = client.post(f"/api/admin/campaigns/{campaign_id}/publish", cookies=cookies)
    assert response.status_code == 200
    
    # Try replace after publish -> should fail
    response = client.post(
        f"/api/admin/campaigns/{campaign_id}/import",
        files={"file": ("test.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        cookies=cookies
    )
    assert response.status_code == 400
    
    # Try delete after publish -> should fail
    response = client.delete(f"/api/admin/campaigns/{campaign_id}", cookies=cookies)
    assert response.status_code == 400
