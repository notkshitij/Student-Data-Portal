"""
Tests for the Student API endpoints.
"""

import uuid
from fastapi.testclient import TestClient

from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_student import CampaignStudent, SubmissionStatus
from app.models.campaign_field import CampaignField
from app.models.imported_field_value import ImportedFieldValue
from app.models.student_response import StudentResponse


def _login_as_student(client: TestClient, mock_google_auth) -> str:
    response = client.post("/api/auth/login", json={"code": "valid_code_student"})
    assert response.status_code == 200
    return response.cookies["session_token"]


def _login_as_admin(client: TestClient, mock_google_auth) -> str:
    response = client.post("/api/auth/login", json={"code": "valid_code_admin"})
    assert response.status_code == 200
    return response.cookies["session_token"]


def test_unauthenticated_access(client: TestClient):
    resp = client.get("/api/student/campaigns")
    assert resp.status_code == 401

    resp2 = client.get(f"/api/student/campaigns/{uuid.uuid4()}")
    assert resp2.status_code == 401


def test_admin_cannot_access_student_endpoints(client: TestClient, admin_user, mock_google_auth):
    token = _login_as_admin(client, mock_google_auth)
    client.cookies.set("session_token", token)
    
    resp = client.get("/api/student/campaigns")
    assert resp.status_code == 403
    assert "Insufficient permissions" in resp.json()["detail"]


def test_student_get_campaigns(client: TestClient, student_user, admin_user, db_session, mock_google_auth):
    # Setup a DRAFT campaign
    c_draft = Campaign(name="Draft Campaign", created_by_id=admin_user.id, status=CampaignStatus.DRAFT)
    db_session.add(c_draft)
    
    # Setup a PUBLISHED campaign for student
    c_pub = Campaign(name="Published Campaign", created_by_id=admin_user.id, status=CampaignStatus.PUBLISHED)
    db_session.add(c_pub)
    
    # Setup a PUBLISHED campaign NOT for student
    c_other = Campaign(name="Other Campaign", created_by_id=admin_user.id, status=CampaignStatus.PUBLISHED)
    db_session.add(c_other)
    db_session.commit()
    
    # Enroll student in draft and pub
    cs_draft = CampaignStudent(campaign_id=c_draft.id, student_id=student_user.id)
    cs_pub = CampaignStudent(campaign_id=c_pub.id, student_id=student_user.id)
    db_session.add_all([cs_draft, cs_pub])
    db_session.commit()

    token = _login_as_student(client, mock_google_auth)
    client.cookies.set("session_token", token)

    resp = client.get("/api/student/campaigns")
    assert resp.status_code == 200
    data = resp.json()
    
    # Only the published campaign should be returned
    assert len(data) == 1
    assert data[0]["campaign_id"] == str(c_pub.id)
    assert data[0]["name"] == "Published Campaign"
    assert data[0]["campaign_status"] == CampaignStatus.PUBLISHED.value
    assert data[0]["submission_status"] == SubmissionStatus.PENDING.value


def test_student_get_campaign_detail_access_controls(client: TestClient, student_user, admin_user, db_session, mock_google_auth):
    # Setup
    c_draft = Campaign(name="Draft Campaign", created_by_id=admin_user.id, status=CampaignStatus.DRAFT)
    c_pub = Campaign(name="Published Campaign", created_by_id=admin_user.id, status=CampaignStatus.PUBLISHED)
    c_other = Campaign(name="Other Campaign", created_by_id=admin_user.id, status=CampaignStatus.PUBLISHED)
    db_session.add_all([c_draft, c_pub, c_other])
    db_session.commit()
    
    cs_draft = CampaignStudent(campaign_id=c_draft.id, student_id=student_user.id)
    cs_pub = CampaignStudent(campaign_id=c_pub.id, student_id=student_user.id)
    db_session.add_all([cs_draft, cs_pub])
    db_session.commit()

    token = _login_as_student(client, mock_google_auth)
    client.cookies.set("session_token", token)

    # Cannot access un-enrolled campaign
    resp1 = client.get(f"/api/student/campaigns/{c_other.id}")
    assert resp1.status_code == 404

    # Cannot access DRAFT campaign
    resp2 = client.get(f"/api/student/campaigns/{c_draft.id}")
    assert resp2.status_code == 404
    
    # Can access PUBLISHED campaign
    resp3 = client.get(f"/api/student/campaigns/{c_pub.id}")
    assert resp3.status_code == 200
    assert resp3.json()["name"] == "Published Campaign"


def test_student_get_campaign_detail_fields_and_collect_logic(client: TestClient, student_user, admin_user, db_session, mock_google_auth):
    c_pub = Campaign(name="Fields Campaign", created_by_id=admin_user.id, status=CampaignStatus.PUBLISHED)
    db_session.add(c_pub)
    db_session.commit()
    
    cs_pub = CampaignStudent(campaign_id=c_pub.id, student_id=student_user.id)
    db_session.add(cs_pub)
    db_session.commit()
    
    # Setup fields
    f1 = CampaignField(campaign_id=c_pub.id, field_name="Name", field_order=1)
    f2 = CampaignField(campaign_id=c_pub.id, field_name="Phone", field_order=2)
    f3 = CampaignField(campaign_id=c_pub.id, field_name="Address", field_order=3)
    db_session.add_all([f1, f2, f3])
    db_session.commit()
    
    # Setup imported values
    # Normal field
    iv1 = ImportedFieldValue(campaign_student_id=cs_pub.id, campaign_field_id=f1.id, imported_value="Alice", requires_student_input=False)
    # Collect field with NO response yet
    iv2 = ImportedFieldValue(campaign_student_id=cs_pub.id, campaign_field_id=f2.id, imported_value="[COLLECT]", requires_student_input=True)
    # Collect field WITH response
    iv3 = ImportedFieldValue(campaign_student_id=cs_pub.id, campaign_field_id=f3.id, imported_value="[COLLECT]", requires_student_input=True)
    db_session.add_all([iv1, iv2, iv3])
    db_session.commit()
    
    sr = StudentResponse(imported_field_value_id=iv3.id, response_value="123 Main St")
    db_session.add(sr)
    db_session.commit()
    
    # Authenticate and get details
    token = _login_as_student(client, mock_google_auth)
    client.cookies.set("session_token", token)

    resp = client.get(f"/api/student/campaigns/{c_pub.id}")
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["campaign_id"] == str(c_pub.id)
    assert len(data["fields"]) == 3
    
    fields = data["fields"]
    # Check ordering
    assert fields[0]["field_name"] == "Name"
    assert fields[1]["field_name"] == "Phone"
    assert fields[2]["field_name"] == "Address"
    
    # Check normal value
    assert fields[0]["requires_student_input"] is False
    assert fields[0]["value"] == "Alice"
    
    # Check collect value WITHOUT response (MUST NOT BE [COLLECT])
    assert fields[1]["requires_student_input"] is True
    assert fields[1]["value"] is None
    
    # Check collect value WITH response
    assert fields[2]["requires_student_input"] is True
    assert fields[2]["value"] == "123 Main St"
