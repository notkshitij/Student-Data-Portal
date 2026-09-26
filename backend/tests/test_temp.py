def test_temp(client, draft_campaign, student_user, mock_google_auth, db_session):
    from app.models.campaign import CampaignStatus
    draft_campaign.status = CampaignStatus.CLOSED
    db_session.commit()
    from tests.test_admin_campaigns import _login_as_student
    _login_as_student(client, mock_google_auth)
    r = client.put(f"/api/student/campaigns/{draft_campaign.id}/responses", json={"responses": {}})
    print(r.json())
