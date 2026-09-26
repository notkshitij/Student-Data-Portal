"""
Tests for Admin Campaign Management API endpoints.
"""

import uuid
from fastapi.testclient import TestClient

from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_student import CampaignStudent, SubmissionStatus
from app.models.campaign_field import CampaignField
from app.models.imported_field_value import ImportedFieldValue
from app.models.student_response import StudentResponse
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole


def _login_as_student(client: TestClient, mock_google_auth) -> str:
    response = client.post("/api/auth/login", json={"code": "valid_code_student"})
    assert response.status_code == 200
    return response.cookies["session_token"]


def _login_as_admin(client: TestClient, mock_google_auth) -> str:
    response = client.post("/api/auth/login", json={"code": "valid_code_admin"})
    assert response.status_code == 200
    return response.cookies["session_token"]


def test_unauthenticated_access(client: TestClient):
    resp = client.get("/api/admin/campaigns")
    assert resp.status_code == 401

    resp2 = client.post(f"/api/admin/campaigns/{uuid.uuid4()}/publish")
    assert resp2.status_code == 401


def test_student_cannot_access_admin_endpoints(client: TestClient, student_user, mock_google_auth):
    token = _login_as_student(client, mock_google_auth)
    client.cookies.set("session_token", token)
    
    resp = client.get("/api/admin/campaigns")
    assert resp.status_code == 403
    
    resp2 = client.post(f"/api/admin/campaigns/{uuid.uuid4()}/publish")
    assert resp2.status_code == 403


def test_admin_list_campaigns(client: TestClient, admin_user, student_user, db_session, mock_google_auth):
    # Create two campaigns
    c1 = Campaign(name="C1", created_by_id=admin_user.id, status=CampaignStatus.DRAFT)
    c2 = Campaign(name="C2", created_by_id=admin_user.id, status=CampaignStatus.PUBLISHED)
    db_session.add_all([c1, c2])
    db_session.commit()
    
    cs1 = CampaignStudent(campaign_id=c1.id, student_id=student_user.id)
    db_session.add(cs1)
    db_session.commit()

    token = _login_as_admin(client, mock_google_auth)
    client.cookies.set("session_token", token)

    resp = client.get("/api/admin/campaigns")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    
    # Verify c1 info
    c1_data = next(c for c in data if c["campaign_id"] == str(c1.id))
    assert c1_data["name"] == "C1"
    assert c1_data["status"] == "DRAFT"
    assert c1_data["student_count"] == 1
    assert c1_data["field_count"] == 0


def test_admin_campaign_detail(client: TestClient, admin_user, student_user, db_session, mock_google_auth):
    c = Campaign(name="C3", created_by_id=admin_user.id, status=CampaignStatus.DRAFT)
    db_session.add(c)
    db_session.commit()
    
    cs = CampaignStudent(campaign_id=c.id, student_id=student_user.id)
    db_session.add(cs)
    db_session.commit()
    
    f1 = CampaignField(campaign_id=c.id, field_name="Name")
    f2 = CampaignField(campaign_id=c.id, field_name="Phone")
    db_session.add_all([f1, f2])
    db_session.commit()
    
    iv1 = ImportedFieldValue(campaign_student_id=cs.id, campaign_field_id=f1.id, imported_value="Alice", requires_student_input=False)
    iv2 = ImportedFieldValue(campaign_student_id=cs.id, campaign_field_id=f2.id, imported_value="[COLLECT]", requires_student_input=True)
    db_session.add_all([iv1, iv2])
    db_session.commit()

    token = _login_as_admin(client, mock_google_auth)
    client.cookies.set("session_token", token)

    resp = client.get(f"/api/admin/campaigns/{c.id}")
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["name"] == "C3"
    assert data["student_count"] == 1
    assert data["field_count"] == 2
    assert data["collect_field_count"] == 1


def test_publish_campaign_flow(client: TestClient, admin_user, student_user, db_session, mock_google_auth):
    # 1. Create campaign
    c = Campaign(name="Publish Me", created_by_id=admin_user.id, status=CampaignStatus.DRAFT)
    db_session.add(c)
    db_session.commit()
    
    cs = CampaignStudent(campaign_id=c.id, student_id=student_user.id)
    db_session.add(cs)
    db_session.commit()
    
    f1 = CampaignField(campaign_id=c.id, field_name="F1")
    db_session.add(f1)
    db_session.commit()
    
    iv = ImportedFieldValue(campaign_student_id=cs.id, campaign_field_id=f1.id, requires_student_input=False)
    db_session.add(iv)
    db_session.commit()
    
    # Log in as admin
    admin_token = _login_as_admin(client, mock_google_auth)
    
    # 2. Check student can't see it yet
    student_token = _login_as_student(client, mock_google_auth)
    client.cookies.set("session_token", student_token)
    
    student_list = client.get("/api/student/campaigns")
    assert str(c.id) not in [camp["campaign_id"] for camp in student_list.json()]
    
    # 3. Publish as admin
    client.cookies.set("session_token", admin_token)
    pub_resp = client.post(f"/api/admin/campaigns/{c.id}/publish")
    assert pub_resp.status_code == 200
    assert pub_resp.json()["message"] == "Campaign published successfully"
    
    db_session.refresh(c)
    assert c.status == CampaignStatus.PUBLISHED
    
    # Check Audit Log
    audit = db_session.query(AuditLog).filter_by(entity_id=str(c.id), action="campaign_published").first()
    assert audit is not None
    assert audit.user_id == admin_user.id
    
    # 4. Check student can see it now
    client.cookies.set("session_token", student_token)
    student_list_after = client.get("/api/student/campaigns")
    assert str(c.id) in [camp["campaign_id"] for camp in student_list_after.json()]


def test_publish_campaign_already_published(client: TestClient, admin_user, db_session, mock_google_auth):
    c = Campaign(name="Already Pub", created_by_id=admin_user.id, status=CampaignStatus.PUBLISHED)
    db_session.add(c)
    db_session.commit()
    
    token = _login_as_admin(client, mock_google_auth)
    client.cookies.set("session_token", token)
    
    resp = client.post(f"/api/admin/campaigns/{c.id}/publish")
    assert resp.status_code == 409


def test_publish_campaign_invalid(client: TestClient, admin_user, db_session, mock_google_auth):
    # Campaign with no students/fields
    c = Campaign(name="Empty", created_by_id=admin_user.id, status=CampaignStatus.DRAFT)
    db_session.add(c)
    db_session.commit()
    
    token = _login_as_admin(client, mock_google_auth)
    client.cookies.set("session_token", token)
    
    resp = client.post(f"/api/admin/campaigns/{c.id}/publish")
    assert resp.status_code == 400
    assert "no students" in resp.json()["detail"]


def test_publish_nonexistent_campaign(client: TestClient, admin_user, mock_google_auth):
    token = _login_as_admin(client, mock_google_auth)
    client.cookies.set("session_token", token)
    
    resp = client.post(f"/api/admin/campaigns/{uuid.uuid4()}/publish")
    assert resp.status_code == 404

# --- Form Configuration Tests ---

def test_get_form_config_unauthenticated(client):
    response = client.get(f"/api/admin/campaigns/{uuid.uuid4()}/form")
    assert response.status_code == 401


def test_get_form_config_as_student(client, student_user, mock_google_auth):
    _login_as_student(client, mock_google_auth)
    response = client.get(f"/api/admin/campaigns/{uuid.uuid4()}/form")
    assert response.status_code == 403


def test_get_form_config_as_admin(client, admin_user, draft_campaign, db_session, mock_google_auth):
    _login_as_admin(client, mock_google_auth)
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/form")
    assert response.status_code == 200
    data = response.json()
    assert data["campaign_id"] == str(draft_campaign.id)
    assert len(data["fields"]) > 0
    # Check default config for collect fields
    for field in data["fields"]:
        if field["requires_student_input"]:
            assert field["validation_config"]["type"] == "text"


def test_update_form_config_as_admin(client, admin_user, draft_campaign, db_session, mock_google_auth):
    _login_as_admin(client, mock_google_auth)
    
    # 1. Fetch current config
    get_resp = client.get(f"/api/admin/campaigns/{draft_campaign.id}/form")
    fields = get_resp.json()["fields"]
    collect_fields = [f for f in fields if f["requires_student_input"]]
    non_collect_fields = [f for f in fields if not f["requires_student_input"]]
    
    assert len(collect_fields) > 0
    target_field = collect_fields[0]
    
    # 2. Update config for a valid collect field with email type
    update_payload = {
        "fields": [
            {
                "id": target_field["id"],
                "validation_config": {
                    "type": "email",
                    "rules": {
                        "required": True,
                        "allowed_domains": ["poornima.edu.in", "poornima.org"]
                    }
                }
            }
        ]
    }
    
    put_resp = client.put(f"/api/admin/campaigns/{draft_campaign.id}/form", json=update_payload)
    assert put_resp.status_code == 200
    
    # 3. Verify it was saved
    verify_resp = client.get(f"/api/admin/campaigns/{draft_campaign.id}/form")
    updated_field = next(f for f in verify_resp.json()["fields"] if f["id"] == target_field["id"])
    assert updated_field["validation_config"]["type"] == "email"
    assert updated_field["validation_config"]["rules"]["required"] is True
    assert "poornima.edu.in" in updated_field["validation_config"]["rules"]["allowed_domains"]


def test_update_form_config_non_collect_field_rejected(client, admin_user, draft_campaign, db_session, mock_google_auth):
    _login_as_admin(client, mock_google_auth)
    
    get_resp = client.get(f"/api/admin/campaigns/{draft_campaign.id}/form")
    fields = get_resp.json()["fields"]
    non_collect_fields = [f for f in fields if not f["requires_student_input"]]
    
    if len(non_collect_fields) > 0:
        target_field = non_collect_fields[0]
        update_payload = {
            "fields": [
                {
                    "id": target_field["id"],
                    "validation_config": {
                        "type": "text",
                        "rules": {"required": True}
                    }
                }
            ]
        }
        
        put_resp = client.put(f"/api/admin/campaigns/{draft_campaign.id}/form", json=update_payload)
        assert put_resp.status_code == 400
        assert "not a collect field" in put_resp.json()["detail"]


def test_update_form_config_invalid_rules_rejected(client, admin_user, draft_campaign, mock_google_auth):
    _login_as_admin(client, mock_google_auth)
    
    get_resp = client.get(f"/api/admin/campaigns/{draft_campaign.id}/form")
    collect_fields = [f for f in get_resp.json()["fields"] if f["requires_student_input"]]
    
    # Text length contradiction
    update_payload = {
        "fields": [{
            "id": collect_fields[0]["id"],
            "validation_config": {
                "type": "text",
                "rules": {"min_length": 10, "max_length": 5}
            }
        }]
    }
    
    put_resp = client.put(f"/api/admin/campaigns/{draft_campaign.id}/form", json=update_payload)
    assert put_resp.status_code == 422 # Pydantic validation error


def test_update_form_config_stale_rules_removed(client, admin_user, draft_campaign, mock_google_auth):
    _login_as_admin(client, mock_google_auth)
    
    get_resp = client.get(f"/api/admin/campaigns/{draft_campaign.id}/form")
    target_field = [f for f in get_resp.json()["fields"] if f["requires_student_input"]][0]
    
    # We pass 'allowed_domains' to a 'number' type. The backend should silently strip it out.
    update_payload = {
        "fields": [{
            "id": target_field["id"],
            "validation_config": {
                "type": "number",
                "rules": {
                    "min_value": 0,
                    "allowed_domains": ["poornima.edu.in"]
                }
            }
        }]
    }
    
    put_resp = client.put(f"/api/admin/campaigns/{draft_campaign.id}/form", json=update_payload)
    assert put_resp.status_code == 200
    
    verify_resp = client.get(f"/api/admin/campaigns/{draft_campaign.id}/form")
    updated_field = next(f for f in verify_resp.json()["fields"] if f["id"] == target_field["id"])
    assert updated_field["validation_config"]["type"] == "number"
    assert "allowed_domains" not in updated_field["validation_config"]["rules"]
    assert updated_field["validation_config"]["rules"]["min_value"] == 0.0


# --- Campaign Progress and Submission List Tests ---

def test_admin_get_campaign_progress_unauthorized(client, draft_campaign):
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/progress")
    assert response.status_code == 401


def test_admin_get_campaign_progress_as_student(client, student_user, draft_campaign, mock_google_auth):
    _login_as_student(client, mock_google_auth)
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/progress")
    assert response.status_code == 403


def test_admin_get_campaign_progress_success(client, admin_user, draft_campaign, mock_google_auth, db_session):
    _login_as_admin(client, mock_google_auth)
    
    # 1 enrolled student (from draft_campaign fixture, student_user)
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/progress")
    assert response.status_code == 200
    data = response.json()
    assert data["total_students"] == 1
    assert data["pending_students"] == 1
    assert data["submitted_students"] == 0
    assert data["submission_percentage"] == 0.0


def test_admin_get_campaign_students_list(client, admin_user, draft_campaign, student_user, mock_google_auth):
    _login_as_admin(client, mock_google_auth)
    
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/students")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == student_user.email
    assert data["items"][0]["status"] == "PENDING"
    

def test_admin_get_campaign_student_detail(client, admin_user, draft_campaign, student_user, mock_google_auth):
    _login_as_admin(client, mock_google_auth)
    
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/students/{student_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == student_user.email
    assert data["status"] == "PENDING"
    assert len(data["fields"]) > 0
    
    # Ensure imported value is present and [COLLECT] marker is shown if it's a collect field
    collect_field = next(f for f in data["fields"] if f["requires_student_input"])
    assert collect_field["imported_value"] == "[COLLECT]"
    assert collect_field["student_response"] is None
    

def test_admin_get_campaign_student_detail_not_enrolled(client, admin_user, draft_campaign, mock_google_auth, db_session):
    _login_as_admin(client, mock_google_auth)
    
    other_student = User(email="other@poornima.edu.in", role=UserRole.STUDENT, is_active=True, google_subject_id="other")
    db_session.add(other_student)
    db_session.commit()
    
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/students/{other_student.id}")
    assert response.status_code == 404

def test_admin_get_campaign_students_list_invalid_status(client, admin_user, draft_campaign, mock_google_auth):
    _login_as_admin(client, mock_google_auth)
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/students?status=INVALID")
    assert response.status_code == 400


def test_admin_get_campaign_students_list_pagination(client, admin_user, draft_campaign, mock_google_auth, db_session):
    # Add another student
    student_2 = User(email="student_2@poornima.edu.in", role=UserRole.STUDENT, is_active=True)
    db_session.add(student_2)
    db_session.commit()
    
    cs2 = CampaignStudent(campaign_id=draft_campaign.id, student_id=student_2.id, status=SubmissionStatus.PENDING)
    db_session.add(cs2)
    db_session.commit()
    
    _login_as_admin(client, mock_google_auth)
    
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/students?page=1&page_size=1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 1


def test_admin_get_campaign_progress_after_submission(client, admin_user, draft_campaign, student_user, mock_google_auth, db_session):
    # Setup SUBMITTED for student 1
    cs1 = db_session.query(CampaignStudent).filter(
        CampaignStudent.campaign_id == draft_campaign.id,
        CampaignStudent.student_id == student_user.id
    ).first()
    cs1.status = SubmissionStatus.SUBMITTED
    
    from app.models.campaign_submission import CampaignSubmission
    sub = CampaignSubmission(campaign_student_id=cs1.id)
    db_session.add(sub)
    db_session.commit()
    
    _login_as_admin(client, mock_google_auth)
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/progress")
    data = response.json()
    assert data["total_students"] == 1
    assert data["pending_students"] == 0
    assert data["submitted_students"] == 1
    assert data["submission_percentage"] == 100.0


def test_admin_get_campaign_student_detail_submitted(client, admin_user, draft_campaign, student_user, mock_google_auth, db_session):
    cs = db_session.query(CampaignStudent).filter(
        CampaignStudent.campaign_id == draft_campaign.id,
        CampaignStudent.student_id == student_user.id
    ).first()
    
    # Get collect field
    iv = next(v for v in cs.imported_field_values if v.requires_student_input)
    field_id = iv.campaign_field_id
    
    # Save a response
    cs.status = SubmissionStatus.SUBMITTED
    
    from app.models.campaign_submission import CampaignSubmission
    sub = CampaignSubmission(campaign_student_id=cs.id)
    db_session.add(sub)
    
    resp = StudentResponse(imported_field_value_id=iv.id, response_value="My Answer")
    db_session.add(resp)
    db_session.commit()
    
    _login_as_admin(client, mock_google_auth)
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/students/{student_user.id}")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "SUBMITTED"
    assert data["submitted_at"] is not None
    
    res_field = next(f for f in data["fields"] if f["field_id"] == str(field_id))
    assert res_field["imported_value"] == "[COLLECT]"
    assert res_field["student_response"] == "My Answer"


def test_admin_get_campaign_student_detail_pending_draft(client, admin_user, draft_campaign, student_user, mock_google_auth, db_session):
    cs = db_session.query(CampaignStudent).filter(
        CampaignStudent.campaign_id == draft_campaign.id,
        CampaignStudent.student_id == student_user.id
    ).first()
    
    iv = next(v for v in cs.imported_field_values if v.requires_student_input)
    field_id = iv.campaign_field_id
    
    # Still PENDING
    cs.status = SubmissionStatus.PENDING
    
    resp = StudentResponse(imported_field_value_id=iv.id, response_value="Draft Answer")
    db_session.add(resp)
    db_session.commit()
    
    _login_as_admin(client, mock_google_auth)
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/students/{student_user.id}")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "PENDING"
    assert data["submitted_at"] is None
    
    res_field = next(f for f in data["fields"] if f["field_id"] == str(field_id))
    assert res_field["student_response"] == "Draft Answer"


# --- Export Tests ---

def test_admin_export_campaign_unauthorized(client, draft_campaign):
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/export")
    assert response.status_code == 401


def test_admin_export_campaign_student_rejected(client, draft_campaign, student_user, mock_google_auth):
    _login_as_student(client, mock_google_auth)
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/export")
    assert response.status_code == 403


def test_admin_export_campaign_success(client, admin_user, draft_campaign, student_user, mock_google_auth, db_session):
    # Setup some values
    cs = db_session.query(CampaignStudent).filter(
        CampaignStudent.campaign_id == draft_campaign.id,
        CampaignStudent.student_id == student_user.id
    ).first()
    
    # We have one collect field (e.g. Phone) and one non-collect (e.g. Name, Email ID*)
    iv_collect = next(v for v in cs.imported_field_values if v.requires_student_input)
    iv_non_collect = next(v for v in cs.imported_field_values if not v.requires_student_input)
    
    collect_field_id = iv_collect.campaign_field_id
    non_collect_field_id = iv_non_collect.campaign_field_id
    
    collect_field_name = next(f.field_name for f in draft_campaign.fields if f.id == collect_field_id)
    non_collect_field_name = next(f.field_name for f in draft_campaign.fields if f.id == non_collect_field_id)
    
    iv_non_collect.imported_value = "Test Name"
    
    # Add formula-injection string as response
    resp = StudentResponse(imported_field_value_id=iv_collect.id, response_value="=1+1")
    db_session.add(resp)
    
    cs.status = SubmissionStatus.SUBMITTED
    from app.models.campaign_submission import CampaignSubmission
    sub = CampaignSubmission(campaign_student_id=cs.id)
    db_session.add(sub)
    
    db_session.commit()
    
    _login_as_admin(client, mock_google_auth)
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment; filename=" in response.headers["content-disposition"]
    
    # Check CSV content
    text = response.text
    lines = text.strip().split("\r\n")
    
    # Header should contain all fields + Submission Status + Submitted At
    header = lines[0].split(",")
    assert header[-2] == "Submission Status"
    assert header[-1] == "Submitted At"
    assert non_collect_field_name in header
    
    # Verify values
    data = lines[1].split(",")
    name_idx = header.index(non_collect_field_name)
    assert data[name_idx] == "Test Name"
    
    phone_idx = header.index(collect_field_name)
    # The formula =1+1 should be sanitized to '=1+1
    assert data[phone_idx] == "'=1+1"
    
    # Verify [COLLECT] isn't present
    assert "[COLLECT]" not in text


def test_admin_export_campaign_pending_and_status_filter(client, admin_user, draft_campaign, student_user, mock_google_auth, db_session):
    cs1 = db_session.query(CampaignStudent).filter(
        CampaignStudent.campaign_id == draft_campaign.id,
        CampaignStudent.student_id == student_user.id
    ).first()
    cs1.status = SubmissionStatus.SUBMITTED
    from app.models.campaign_submission import CampaignSubmission
    sub = CampaignSubmission(campaign_student_id=cs1.id)
    db_session.add(sub)
    db_session.commit()

    # Add a second pending student
    student_2 = User(email="student_2@poornima.edu.in", role=UserRole.STUDENT, is_active=True)
    db_session.add(student_2)
    db_session.commit()
    
    cs2 = CampaignStudent(campaign_id=draft_campaign.id, student_id=student_2.id, status=SubmissionStatus.PENDING)
    db_session.add(cs2)
    db_session.commit()
    
    _login_as_admin(client, mock_google_auth)
    
    # Invalid status -> 400
    resp_invalid = client.get(f"/api/admin/campaigns/{draft_campaign.id}/export?status=INVALID")
    assert resp_invalid.status_code == 400
    
    # Pending only
    resp_pending = client.get(f"/api/admin/campaigns/{draft_campaign.id}/export?status=PENDING")
    assert resp_pending.status_code == 200
    
    # PENDING filter should only return student_2
    lines = resp_pending.text.strip().split("\r\n")
    # 1 header + 1 student
    assert len(lines) == 2
    assert "PENDING" in lines[1]
    
    # SUBMITTED only
    resp_sub = client.get(f"/api/admin/campaigns/{draft_campaign.id}/export?status=SUBMITTED")
    # 1 header + 1 student (student 1 was SUBMITTED)
    lines_sub = resp_sub.text.strip().split("\r\n")
    assert len(lines_sub) == 2
    assert "SUBMITTED" in lines_sub[1]



def test_admin_export_campaign_csv_parsing_and_isolation(client, admin_user, draft_campaign, student_user, mock_google_auth, db_session):
    import csv
    import io

    cs1 = db_session.query(CampaignStudent).filter(
        CampaignStudent.campaign_id == draft_campaign.id,
        CampaignStudent.student_id == student_user.id
    ).first()
    
    # We have one collect field (e.g. Phone) and one non-collect (e.g. Name, Email ID*)
    iv_collect = next(v for v in cs1.imported_field_values if v.requires_student_input)
    iv_non_collect = next(v for v in cs1.imported_field_values if not v.requires_student_input)
    
    collect_field_id = iv_collect.campaign_field_id
    non_collect_field_id = iv_non_collect.campaign_field_id
    
    collect_field_name = next(f.field_name for f in draft_campaign.fields if f.id == collect_field_id)
    non_collect_field_name = next(f.field_name for f in draft_campaign.fields if f.id == non_collect_field_id)
    
    # Inject commas, quotes and newlines into non-collect field
    iv_non_collect.imported_value = "He said \"Hello\",\r\nLine two"
    
    # Formula injection testing
    # We will test "=" in the collect field for cs1
    resp = StudentResponse(imported_field_value_id=iv_collect.id, response_value="=1+1")
    db_session.add(resp)
    
    cs1.status = SubmissionStatus.SUBMITTED
    from app.models.campaign_submission import CampaignSubmission
    sub1 = CampaignSubmission(campaign_student_id=cs1.id)
    db_session.add(sub1)
    
    # Add another student with PENDING to test "[COLLECT]" handling for pending
    student_2 = User(email="student_2@poornima.edu.in", role=UserRole.STUDENT, is_active=True)
    db_session.add(student_2)
    db_session.commit()
    
    cs2 = CampaignStudent(campaign_id=draft_campaign.id, student_id=student_2.id, status=SubmissionStatus.PENDING)
    db_session.add(cs2)
    db_session.commit()
    
    # Needs imported field values
    iv2_collect = ImportedFieldValue(campaign_field_id=collect_field_id, campaign_student_id=cs2.id, imported_value="[COLLECT]", requires_student_input=True)
    iv2_non_collect = ImportedFieldValue(campaign_field_id=non_collect_field_id, campaign_student_id=cs2.id, imported_value="-50", requires_student_input=False)
    db_session.add(iv2_collect)
    db_session.add(iv2_non_collect)
    db_session.commit()
    
    # Add a draft student
    student_3 = User(email="student_3@poornima.edu.in", role=UserRole.STUDENT, is_active=True)
    db_session.add(student_3)
    db_session.commit()
    
    cs3 = CampaignStudent(campaign_id=draft_campaign.id, student_id=student_3.id, status=SubmissionStatus.PENDING)
    db_session.add(cs3)
    db_session.commit()
    
    iv3_collect = ImportedFieldValue(campaign_field_id=collect_field_id, campaign_student_id=cs3.id, imported_value="[COLLECT]", requires_student_input=True)
    iv3_non_collect = ImportedFieldValue(campaign_field_id=non_collect_field_id, campaign_student_id=cs3.id, imported_value="@formula", requires_student_input=False)
    db_session.add(iv3_collect)
    db_session.add(iv3_non_collect)
    db_session.commit()
    
    resp3 = StudentResponse(imported_field_value_id=iv3_collect.id, response_value="+draft")
    db_session.add(resp3)
    db_session.commit()

    # Create another campaign to test isolation
    campaign2 = Campaign(name="Other Campaign", status=CampaignStatus.DRAFT, created_by_id=admin_user.id)
    db_session.add(campaign2)
    db_session.commit()
    
    cs_other = CampaignStudent(campaign_id=campaign2.id, student_id=student_2.id, status=SubmissionStatus.PENDING)
    db_session.add(cs_other)
    db_session.commit()
    
    # We should have 3 students in draft_campaign, 1 in campaign2
    _login_as_admin(client, mock_google_auth)
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/export")
    assert response.status_code == 200
    
    # Parse actual CSV
    f = io.StringIO(response.text)
    reader = csv.reader(f)
    rows = list(reader)
    
    header = rows[0]
    assert header[-2] == "Submission Status"
    assert header[-1] == "Submitted At"
    
    # Verify isolation
    assert len(rows) == 4 # 1 header + 3 students (no cs_other)
    
    name_idx = header.index(non_collect_field_name)
    phone_idx = header.index(collect_field_name)
    status_idx = header.index("Submission Status")
    
    # We need to map rows by email or assume order isn't guaranteed
    row1 = next(r for r in rows[1:] if r[status_idx] == "SUBMITTED")
    row2 = next(r for r in rows[1:] if r[name_idx] == "'-50") # -50 sanitized
    row3 = next(r for r in rows[1:] if r[name_idx] == "'@formula") # @formula sanitized
    
    # Test real CSV parsing (newlines, quotes, commas)
    assert row1[name_idx] == "He said \"Hello\",\r\nLine two"
    assert row1[phone_idx] == "'=1+1" # Formula injected and sanitized
    
    # Test [COLLECT] behavior without response (pending)
    assert row2[phone_idx] == "" # empty, not [COLLECT]
    assert "[COLLECT]" not in response.text
    
    # Test [COLLECT] behavior with draft response (pending)
    assert row3[phone_idx] == "'+draft"
    
    # Verify negative numbers are prefixed
    # Notice how we checked row2[name_idx] == "'-50". This intentionally prefixes '-' with "'" to prevent spreadsheet bugs.

def test_admin_export_filename_sanitization_and_audit(client, admin_user, draft_campaign, mock_google_auth, db_session):
    draft_campaign.name = "Student Data / 2026: Final"
    db_session.commit()
    
    _login_as_admin(client, mock_google_auth)
    
    response = client.get(f"/api/admin/campaigns/{draft_campaign.id}/export")
    assert response.status_code == 200
    
    disposition = response.headers["content-disposition"]
    # Check filename is sanitized
    assert "Student_Data___2026__Final-verified-data.csv" in disposition
    
    # Check audit log
    audit_log = db_session.query(AuditLog).filter(
        AuditLog.action == "campaign_export",
        AuditLog.entity_id == str(draft_campaign.id)
    ).first()
    
    assert audit_log is not None
    assert audit_log.user_id == admin_user.id
    assert audit_log.details["status_filter"] == "ALL"


# --- Campaign Closing Tests ---

def test_admin_close_campaign_unauthorized(client, draft_campaign, db_session):
    draft_campaign.status = CampaignStatus.PUBLISHED
    db_session.commit()
    response = client.post(f"/api/admin/campaigns/{draft_campaign.id}/close")
    assert response.status_code == 401


def test_admin_close_campaign_student_rejected(client, draft_campaign, student_user, mock_google_auth, db_session):
    draft_campaign.status = CampaignStatus.PUBLISHED
    db_session.commit()
    _login_as_student(client, mock_google_auth)
    response = client.post(f"/api/admin/campaigns/{draft_campaign.id}/close")
    assert response.status_code == 403


def test_admin_close_campaign_draft_rejected(client, admin_user, draft_campaign, mock_google_auth):
    _login_as_admin(client, mock_google_auth)
    response = client.post(f"/api/admin/campaigns/{draft_campaign.id}/close")
    assert response.status_code == 400
    assert "Only PUBLISHED campaigns can be closed" in response.json()["detail"]


def test_admin_close_campaign_success(client, admin_user, draft_campaign, mock_google_auth, db_session):
    draft_campaign.status = CampaignStatus.PUBLISHED
    db_session.commit()
    _login_as_admin(client, mock_google_auth)
    
    response = client.post(f"/api/admin/campaigns/{draft_campaign.id}/close")
    assert response.status_code == 200
    assert response.json()["message"] == "Campaign closed successfully"
    
    # Check DB
    db_session.refresh(draft_campaign)
    assert draft_campaign.status == CampaignStatus.CLOSED
    
    # Audit log check
    audit_log = db_session.query(AuditLog).filter(
        AuditLog.action == "campaign_closed",
        AuditLog.entity_id == str(draft_campaign.id)
    ).first()
    assert audit_log is not None
    assert audit_log.user_id == admin_user.id
    
    # Closing already closed returns success message
    response2 = client.post(f"/api/admin/campaigns/{draft_campaign.id}/close")
    assert response2.status_code == 200
    assert response2.json()["message"] == "Campaign is already closed"


def test_student_cannot_modify_responses_in_closed_campaign(client, draft_campaign, student_user, mock_google_auth, db_session):
    # Setup SUBMITTED student
    cs1 = db_session.query(CampaignStudent).filter(
        CampaignStudent.campaign_id == draft_campaign.id,
        CampaignStudent.student_id == student_user.id
    ).first()
    
    # We close the campaign
    draft_campaign.status = CampaignStatus.CLOSED
    db_session.commit()
    
    # Try to modify responses
    _login_as_student(client, mock_google_auth)
    response = client.put(f"/api/student/campaigns/{draft_campaign.id}/responses", json={"responses": []})
    assert response.status_code == 400
    assert "Campaign is closed and no longer accepts changes" in response.json()["detail"]
    
    # Try to submit
    response_submit = client.post(f"/api/student/campaigns/{draft_campaign.id}/submit")
    assert response_submit.status_code == 400
    assert "Campaign is closed and no longer accepts changes" in response_submit.json()["detail"]
