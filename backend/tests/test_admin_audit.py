import uuid
import pytest
from datetime import datetime, timezone
from app.models.audit_log import AuditLog
from tests.test_admin_campaigns import _login_as_student, _login_as_admin
from app.models.campaign import CampaignStatus

def test_admin_get_audit_logs_unauthenticated(client):
    response = client.get("/api/admin/audit-logs")
    assert response.status_code == 401


def test_admin_get_audit_logs_student(client, mock_google_auth, student_user):
    _login_as_student(client, mock_google_auth)
    response = client.get("/api/admin/audit-logs")
    assert response.status_code == 403


def test_admin_get_audit_logs_success(client, mock_google_auth, db_session, admin_user):
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    # Setup some audit logs
    al1 = AuditLog(user_id=admin_user.id, action="test_action_1", entity_type="test_entity", entity_id="1", details={"k1": "v1"}, created_at=now - timedelta(minutes=1))
    db_session.add(al1)
    al2 = AuditLog(user_id=admin_user.id, action="test_action_2", entity_type="campaign", entity_id="2", details={"k2": "v2"}, created_at=now)
    db_session.add(al2)
    db_session.commit()

    _login_as_admin(client, mock_google_auth)
    response = client.get("/api/admin/audit-logs")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 2
    
    # Filter only our actions
    test_logs = [item for item in data["items"] if item["action"].startswith("test_action_")]
    assert len(test_logs) == 2
    # Check newest first
    assert test_logs[0]["action"] == "test_action_2"
    assert test_logs[1]["action"] == "test_action_1"


def test_admin_get_audit_logs_pagination(client, mock_google_auth, db_session, admin_user):
    for i in range(5):
        db_session.add(AuditLog(user_id=admin_user.id, action=f"page_action_{i}", entity_type="page_entity", entity_id="1"))
    db_session.commit()
    
    _login_as_admin(client, mock_google_auth)
    response = client.get("/api/admin/audit-logs?page=1&page_size=2&action=page_action_4")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    
    response = client.get("/api/admin/audit-logs?page=100&page_size=50")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 0
    
    response = client.get("/api/admin/audit-logs?page=0&page_size=50")
    assert response.status_code == 400


def test_admin_get_audit_logs_filters(client, mock_google_auth, db_session, admin_user):
    cid = uuid.uuid4()
    al1 = AuditLog(user_id=admin_user.id, action="filter_action", entity_type="campaign", entity_id=str(cid))
    db_session.add(al1)
    db_session.commit()
    
    _login_as_admin(client, mock_google_auth)
    response = client.get(f"/api/admin/audit-logs?action=filter_action")
    assert len(response.json()["items"]) == 1
    
    response = client.get(f"/api/admin/audit-logs?campaign_id={cid}")
    assert len(response.json()["items"]) == 1
    
    response = client.get(f"/api/admin/audit-logs?entity_type=campaign&campaign_id={cid}")
    assert len(response.json()["items"]) == 1


def test_admin_get_audit_logs_sanitization(client, mock_google_auth, db_session, admin_user):
    al1 = AuditLog(
        user_id=admin_user.id,
        action="sanitize_action",
        entity_type="test",
        entity_id="1",
        details={"token": "secret_token", "normal": "data"}
    )
    db_session.add(al1)
    db_session.commit()
    
    _login_as_admin(client, mock_google_auth)
    response = client.get(f"/api/admin/audit-logs?action=sanitize_action")
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert "token" not in item["details"]
    assert item["details"]["normal"] == "data"


def test_campaign_isolation_audit_logs(client, mock_google_auth, db_session, admin_user):
    cid1 = uuid.uuid4()
    cid2 = uuid.uuid4()
    
    al1 = AuditLog(user_id=admin_user.id, action="iso_action", entity_type="campaign", entity_id=str(cid1))
    al2 = AuditLog(user_id=admin_user.id, action="iso_action", entity_type="campaign", entity_id=str(cid2))
    db_session.add_all([al1, al2])
    db_session.commit()
    
    _login_as_admin(client, mock_google_auth)
    response = client.get(f"/api/admin/audit-logs?campaign_id={cid1}")
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["entity_id"] == str(cid1)

