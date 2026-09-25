"""
Tests for Admin Campaign Management API endpoints.
"""

import uuid
from fastapi.testclient import TestClient

from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_student import CampaignStudent
from app.models.campaign_field import CampaignField
from app.models.imported_field_value import ImportedFieldValue
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

