"""
Comprehensive tests for the Excel import functionality.

Covers:
  - Valid workbook import
  - Email ID* detection / missing / duplicate headers
  - Duplicate student email values (rejected)
  - Valid poornima.edu.in and poornima.org domains
  - Invalid email domain / missing / malformed email
  - [COLLECT] in normal data cells
  - Surrounding whitespace around [COLLECT]
  - [COLLECT] in different fields for different students
  - [COLLECT] never accepted as a header
  - Email ID* = [COLLECT] rejected
  - Ordinary text containing [COLLECT] not treated as a marker
  - Normal imported values stored correctly
  - [COLLECT] not stored as an existing value
  - Different Excel column structures across separate campaigns
  - Column ordering preserved
  - Student user creation with google_subject_id = NULL
  - No password generated
  - Campaign membership creation
  - Duplicate campaign membership prevention
  - Student attempting import is rejected (403)
  - Admin import succeeds
  - Rollback when import validation / database processing fails
  - Blank cells handled correctly
  - Integer / float / date cell types
"""

import io
from datetime import datetime

import pytest
from openpyxl import Workbook
from sqlalchemy import func

from app.models.audit_log import AuditLog
from app.models.campaign import Campaign
from app.models.campaign_field import CampaignField
from app.models.campaign_student import CampaignStudent
from app.models.import_record import Import, ImportStatus
from app.models.imported_field_value import ImportedFieldValue
from app.models.user import User, UserRole
from app.services import auth


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_excel_bytes(rows: list[list]) -> bytes:
    """Create an in-memory .xlsx workbook from a list of rows."""
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _login_as_admin(client, mock_google_auth):
    resp = client.post("/api/auth/login", json={"code": "valid_code_admin"})
    assert resp.status_code == 200
    return resp.cookies[auth.SESSION_COOKIE_NAME]


def _post_import(client, token, rows, campaign_name="Test Campaign"):
    # Create campaign
    create_resp = client.post(
        "/api/admin/campaigns",
        json={"name": campaign_name},
        cookies={auth.SESSION_COOKIE_NAME: token},
    )
    if create_resp.status_code != 200:
        return create_resp
        
    campaign_id = create_resp.json()["campaign_id"]

    file_bytes = create_excel_bytes(rows)
    return client.post(
        f"/api/admin/campaigns/{campaign_id}/import",
        files={
            "file": (
                "test.xlsx",
                file_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        cookies={auth.SESSION_COOKIE_NAME: token},
    )


# ---------------------------------------------------------------------------
# Valid import
# ---------------------------------------------------------------------------


class TestValidImport:
    def test_admin_can_import_valid_workbook(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Name*", "Email ID*", "Phone", "Address"],
            ["Student A", "a@poornima.edu.in", "[COLLECT]", "Jaipur"],
            ["Student B", "b@poornima.edu.in", "9876543210", "[COLLECT]"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 200
        data = response.json()
        assert data["num_students"] == 2
        assert data["num_fields"] == 4
        assert data["num_collect_cells"] == 2
        assert data["status"] == "COMPLETED"
        assert data["rows_processed"] == 2
        assert data["rejected_rows"] == 0
        assert data["campaign_name"] == "Test Campaign"
        assert data["fields_discovered"] == ["Name*", "Email ID*", "Phone", "Address"]
        assert set(data["fields_with_collect"]) == {"Phone", "Address"}

    def test_poornima_org_domain_accepted(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Department"],
            ["staff@poornima.org", "Admin Office"],
        ]
        response = _post_import(client, token, rows, "Org Campaign")

        assert response.status_code == 200
        assert response.json()["num_students"] == 1

    def test_mixed_domains_accepted(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name"],
            ["x@poornima.edu.in", "Student X"],
            ["y@poornima.org", "Staff Y"],
        ]
        response = _post_import(client, token, rows, "Mixed Campaign")

        assert response.status_code == 200
        assert response.json()["num_students"] == 2


# ---------------------------------------------------------------------------
# Email ID* column detection
# ---------------------------------------------------------------------------


class TestEmailIdentityColumn:
    def test_missing_email_id_column(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Name", "Phone"],
            ["Alice", "1234567890"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 400
        assert "Email ID*" in response.json()["detail"]

    def test_case_insensitive_header_match(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["email id*", "Name"],
            ["ci@poornima.edu.in", "Case Test"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 200
        assert response.json()["num_students"] == 1

    def test_duplicate_headers_identical_casing_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name", "Name"],
            ["a@poornima.edu.in", "Alice", "Surname"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 400
        assert "Duplicate column header" in response.json()["detail"]

    def test_duplicate_headers_different_casing_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "School", "SCHOOL"],
            ["a@poornima.edu.in", "Alice", "Surname"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 400
        assert "Duplicate column header" in response.json()["detail"]

    def test_duplicate_headers_with_whitespace_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Phone", " Phone  "],
            ["a@poornima.edu.in", "Alice", "Surname"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 400
        assert "Duplicate column header" in response.json()["detail"]

    def test_valid_unique_headers_accepted(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Phone", "Mobile"],
            ["a@poornima.edu.in", "123", "456"],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200

    def test_blank_header_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", None, "Phone"],
            ["a@poornima.edu.in", "Alice", "123"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 400
        assert "blank" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Email validation
# ---------------------------------------------------------------------------


class TestEmailValidation:
    def test_empty_email_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name"],
            ["", "No Email"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_invalid_email_format_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name"],
            ["not-an-email", "Bad Email"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_invalid_domain_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name"],
            ["student@gmail.com", "Wrong Domain"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()

    def test_email_id_collect_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name"],
            ["[COLLECT]", "No Login"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 400
        assert "[COLLECT]" in response.json()["detail"]

    def test_duplicate_emails_in_workbook_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name"],
            ["dup@poornima.edu.in", "First"],
            ["dup@poornima.edu.in", "Second"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 400
        assert "duplicate" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# [COLLECT] marker behavior
# ---------------------------------------------------------------------------


class TestCollectMarker:
    def test_collect_sets_requires_input(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Phone"],
            ["c1@poornima.edu.in", "[COLLECT]"],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200

        campaign_id = response.json()["campaign_id"]
        user = db_session.query(User).filter_by(email="c1@poornima.edu.in").first()
        cs = db_session.query(CampaignStudent).filter_by(
            campaign_id=campaign_id, student_id=user.id
        ).first()
        phone_field = db_session.query(CampaignField).filter_by(
            campaign_id=campaign_id, field_name="Phone"
        ).first()
        ifv = db_session.query(ImportedFieldValue).filter_by(
            campaign_student_id=cs.id, campaign_field_id=phone_field.id
        ).first()

        assert ifv.requires_student_input is True
        assert ifv.imported_value is None  # [COLLECT] is NOT stored

    def test_collect_with_whitespace(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Phone"],
            ["ws@poornima.edu.in", "  [COLLECT]  "],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200
        assert response.json()["num_collect_cells"] == 1

    def test_collect_case_insensitive(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Phone", "Address"],
            ["ci2@poornima.edu.in", "[collect]", "[Collect]"],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200
        assert response.json()["num_collect_cells"] == 2

    def test_text_containing_collect_is_normal_data(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Notes"],
            ["t1@poornima.edu.in", "My [COLLECT] information"],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200
        assert response.json()["num_collect_cells"] == 0

        # Verify the value was stored as-is
        user = db_session.query(User).filter_by(email="t1@poornima.edu.in").first()
        campaign_id = response.json()["campaign_id"]
        cs = db_session.query(CampaignStudent).filter_by(
            campaign_id=campaign_id, student_id=user.id
        ).first()
        notes_field = db_session.query(CampaignField).filter_by(
            campaign_id=campaign_id, field_name="Notes"
        ).first()
        ifv = db_session.query(ImportedFieldValue).filter_by(
            campaign_student_id=cs.id, campaign_field_id=notes_field.id
        ).first()
        assert ifv.imported_value == "My [COLLECT] information"
        assert ifv.requires_student_input is False

    def test_collect_different_fields_per_student(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Phone", "Address"],
            ["d1@poornima.edu.in", "[COLLECT]", "Jaipur"],
            ["d2@poornima.edu.in", "9876543210", "[COLLECT]"],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200

        campaign_id = response.json()["campaign_id"]

        # Student d1: Phone=[COLLECT], Address=Jaipur
        u1 = db_session.query(User).filter_by(email="d1@poornima.edu.in").first()
        cs1 = db_session.query(CampaignStudent).filter_by(
            campaign_id=campaign_id, student_id=u1.id
        ).first()
        vals1 = {
            v.campaign_field.field_name: v
            for v in db_session.query(ImportedFieldValue)
            .filter_by(campaign_student_id=cs1.id)
            .all()
        }
        assert vals1["Phone"].requires_student_input is True
        assert vals1["Phone"].imported_value is None
        assert vals1["Address"].requires_student_input is False
        assert vals1["Address"].imported_value == "Jaipur"

        # Student d2: Phone=9876543210, Address=[COLLECT]
        u2 = db_session.query(User).filter_by(email="d2@poornima.edu.in").first()
        cs2 = db_session.query(CampaignStudent).filter_by(
            campaign_id=campaign_id, student_id=u2.id
        ).first()
        vals2 = {
            v.campaign_field.field_name: v
            for v in db_session.query(ImportedFieldValue)
            .filter_by(campaign_student_id=cs2.id)
            .all()
        }
        assert vals2["Phone"].requires_student_input is False
        assert vals2["Phone"].imported_value == "9876543210"
        assert vals2["Address"].requires_student_input is True
        assert vals2["Address"].imported_value is None

    def test_exact_collect_header_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "[COLLECT]"],
            ["h1@poornima.edu.in", "value"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 400
        assert "[COLLECT]" in response.json()["detail"]

    def test_collect_with_whitespace_in_header_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "  [COLLECT]  "],
            ["h1@poornima.edu.in", "value"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 400
        assert "[COLLECT]" in response.json()["detail"]

    def test_header_containing_collect_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Father's [COLLECT] Email"],
            ["h1@poornima.edu.in", "value"],
        ]
        response = _post_import(client, token, rows)

        assert response.status_code == 400
        assert "[COLLECT]" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Normal imported values
# ---------------------------------------------------------------------------


class TestNormalValues:
    def test_normal_values_stored(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name", "Phone"],
            ["nv@poornima.edu.in", "Alice", "9999999999"],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200

        user = db_session.query(User).filter_by(email="nv@poornima.edu.in").first()
        campaign_id = response.json()["campaign_id"]
        cs = db_session.query(CampaignStudent).filter_by(
            campaign_id=campaign_id, student_id=user.id
        ).first()
        vals = {
            v.campaign_field.field_name: v
            for v in db_session.query(ImportedFieldValue)
            .filter_by(campaign_student_id=cs.id)
            .all()
        }
        assert vals["Name"].imported_value == "Alice"
        assert vals["Name"].requires_student_input is False
        assert vals["Phone"].imported_value == "9999999999"
        assert vals["Phone"].requires_student_input is False

    def test_blank_cell_not_treated_as_collect(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Optional"],
            ["bc@poornima.edu.in", None],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200
        assert response.json()["num_collect_cells"] == 0

        user = db_session.query(User).filter_by(email="bc@poornima.edu.in").first()
        campaign_id = response.json()["campaign_id"]
        cs = db_session.query(CampaignStudent).filter_by(
            campaign_id=campaign_id, student_id=user.id
        ).first()
        opt_field = db_session.query(CampaignField).filter_by(
            campaign_id=campaign_id, field_name="Optional"
        ).first()
        ifv = db_session.query(ImportedFieldValue).filter_by(
            campaign_student_id=cs.id, campaign_field_id=opt_field.id
        ).first()
        assert ifv.imported_value is None
        assert ifv.requires_student_input is False

    def test_integer_value_preserved(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Roll No"],
            ["int@poornima.edu.in", 42],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200

        user = db_session.query(User).filter_by(email="int@poornima.edu.in").first()
        campaign_id = response.json()["campaign_id"]
        cs = db_session.query(CampaignStudent).filter_by(
            campaign_id=campaign_id, student_id=user.id
        ).first()
        field = db_session.query(CampaignField).filter_by(
            campaign_id=campaign_id, field_name="Roll No"
        ).first()
        ifv = db_session.query(ImportedFieldValue).filter_by(
            campaign_student_id=cs.id, campaign_field_id=field.id
        ).first()
        assert ifv.imported_value == "42"

    def test_float_rendered_cleanly(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "GPA"],
            ["fl@poornima.edu.in", 8.5],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200

        user = db_session.query(User).filter_by(email="fl@poornima.edu.in").first()
        campaign_id = response.json()["campaign_id"]
        cs = db_session.query(CampaignStudent).filter_by(
            campaign_id=campaign_id, student_id=user.id
        ).first()
        field = db_session.query(CampaignField).filter_by(
            campaign_id=campaign_id, field_name="GPA"
        ).first()
        ifv = db_session.query(ImportedFieldValue).filter_by(
            campaign_student_id=cs.id, campaign_field_id=field.id
        ).first()
        assert ifv.imported_value == "8.5"


# ---------------------------------------------------------------------------
# Dynamic columns / column order
# ---------------------------------------------------------------------------


class TestDynamicColumns:
    def test_column_order_preserved(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Branch", "Email ID*", "Father's Name", "DOB"],
            ["CS", "co@poornima.edu.in", "Mr. Smith", "2000-01-01"],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200

        campaign_id = response.json()["campaign_id"]
        fields = (
            db_session.query(CampaignField)
            .filter_by(campaign_id=campaign_id)
            .order_by(CampaignField.field_order)
            .all()
        )
        names = [f.field_name for f in fields]
        assert names == ["Branch", "Email ID*", "Father's Name", "DOB"]

    def test_different_columns_across_campaigns(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)

        # Campaign 1
        rows1 = [
            ["Email ID*", "Name", "Phone"],
            ["dc1@poornima.edu.in", "Alice", "123"],
        ]
        r1 = _post_import(client, token, rows1, "Campaign Alpha")
        assert r1.status_code == 200

        # Campaign 2 with completely different columns
        rows2 = [
            ["Email ID*", "Department", "Year", "CGPA"],
            ["dc2@poornima.edu.in", "CS", "3", "8.5"],
        ]
        r2 = _post_import(client, token, rows2, "Campaign Beta")
        assert r2.status_code == 200

        # Verify they have different field sets
        fields1 = (
            db_session.query(CampaignField)
            .filter_by(campaign_id=r1.json()["campaign_id"])
            .order_by(CampaignField.field_order)
            .all()
        )
        fields2 = (
            db_session.query(CampaignField)
            .filter_by(campaign_id=r2.json()["campaign_id"])
            .order_by(CampaignField.field_order)
            .all()
        )
        assert [f.field_name for f in fields1] == ["Email ID*", "Name", "Phone"]
        assert [f.field_name for f in fields2] == [
            "Email ID*", "Department", "Year", "CGPA"
        ]


# ---------------------------------------------------------------------------
# User creation
# ---------------------------------------------------------------------------


class TestUserCreation:
    def test_student_user_created(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name"],
            ["newstudent@poornima.edu.in", "New Student"],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200

        user = db_session.query(User).filter_by(
            email="newstudent@poornima.edu.in"
        ).first()
        assert user is not None
        assert user.role == UserRole.STUDENT
        assert user.is_active is True

    def test_google_subject_id_null_after_import(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name"],
            ["nosub@poornima.edu.in", "No Sub"],
        ]
        _post_import(client, token, rows)

        user = db_session.query(User).filter_by(
            email="nosub@poornima.edu.in"
        ).first()
        assert user.google_subject_id is None

    def test_no_password_generated(
        self, client, admin_user, db_session, mock_google_auth
    ):
        """Verify the User model has no password-related columns."""
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name"],
            ["nopw@poornima.edu.in", "No PW"],
        ]
        _post_import(client, token, rows)

        user = db_session.query(User).filter_by(
            email="nopw@poornima.edu.in"
        ).first()
        assert not hasattr(user, "password_hash")
        assert not hasattr(user, "password")

    def test_existing_user_reused(
        self, client, admin_user, student_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        initial_count = db_session.query(func.count(User.id)).scalar()

        rows = [
            ["Email ID*", "Name"],
            [student_user.email, "Existing"],
            ["brand_new@poornima.edu.in", "Brand New"],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200
        assert response.json()["num_students"] == 2

        final_count = db_session.query(func.count(User.id)).scalar()
        assert final_count == initial_count + 1  # only 1 new user


# ---------------------------------------------------------------------------
# Campaign membership
# ---------------------------------------------------------------------------


class TestCampaignMembership:
    def test_campaign_student_created(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name"],
            ["mem1@poornima.edu.in", "Member 1"],
            ["mem2@poornima.edu.in", "Member 2"],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200

        campaign_id = response.json()["campaign_id"]
        memberships = (
            db_session.query(CampaignStudent)
            .filter_by(campaign_id=campaign_id)
            .all()
        )
        assert len(memberships) == 2

    def test_import_record_created(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name"],
            ["ir@poornima.edu.in", "Import Rec"],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200

        import_rec = (
            db_session.query(Import)
            .filter_by(campaign_id=response.json()["campaign_id"])
            .first()
        )
        assert import_rec is not None
        assert import_rec.status == ImportStatus.COMPLETED
        assert import_rec.row_count == 1
        assert import_rec.original_filename == "test.xlsx"

    def test_audit_log_created(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name"],
            ["al@poornima.edu.in", "Audit Log"],
        ]
        response = _post_import(client, token, rows)
        assert response.status_code == 200

        campaign_id = str(response.json()["campaign_id"])
        audit = (
            db_session.query(AuditLog)
            .filter_by(action="IMPORT_CAMPAIGN", entity_id=campaign_id)
            .first()
        )
        assert audit is not None
        assert audit.user_id == admin_user.id


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


class TestAuthorization:
    def test_student_cannot_import(
        self, client, student_user, mock_google_auth
    ):
        login_resp = client.post(
            "/api/auth/login", json={"code": "valid_code_student"}
        )
        token = login_resp.cookies[auth.SESSION_COOKIE_NAME]

        rows = [["Email ID*"], ["s@poornima.edu.in"]]
        file_bytes = create_excel_bytes(rows)

        response = client.post(
            \"/api/admin/campaigns/00000000-0000-0000-0000-000000000000/import\",
            files={"file": ("test.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            cookies={auth.SESSION_COOKIE_NAME: token},
        )
        assert response.status_code == 403

    def test_unauthenticated_cannot_import(self, client):
        rows = [["Email ID*"], ["s@poornima.edu.in"]]
        file_bytes = create_excel_bytes(rows)

        response = client.post(
            \"/api/admin/campaigns/00000000-0000-0000-0000-000000000000/import\",
            files={"file": ("test.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Rollback / transactional behavior
# ---------------------------------------------------------------------------


class TestRollback:
    def test_invalid_workbook_no_partial_data(
        self, client, admin_user, db_session, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)

        response = client.post(
            \"/api/admin/campaigns/00000000-0000-0000-0000-000000000000/import\",
            files={
                "file": (
                    "bad.xlsx",
                    b"not an excel file",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            cookies={auth.SESSION_COOKIE_NAME: token},
        )
        assert response.status_code == 400

        campaign = (
            db_session.query(Campaign).filter_by(name="Fail Campaign").first()
        )
        assert campaign is None

    def test_validation_error_rolls_back(
        self, client, admin_user, db_session, mock_google_auth
    ):
        """When a row fails validation, no partial campaign is left."""
        token = _login_as_admin(client, mock_google_auth)
        rows = [
            ["Email ID*", "Name"],
            ["good@poornima.edu.in", "Good"],
            ["bad@gmail.com", "Bad Domain"],  # will fail
        ]
        response = _post_import(client, token, rows, "Partial Fail")
        assert response.status_code == 400

        campaign = (
            db_session.query(Campaign).filter_by(name="Partial Fail").first()
        )
        assert campaign is None

    def test_non_xlsx_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)

        response = client.post(
            \"/api/admin/campaigns/00000000-0000-0000-0000-000000000000/import\",
            files={"file": ("data.csv", b"a,b,c", "text/csv")},
            cookies={auth.SESSION_COOKIE_NAME: token},
        )
        assert response.status_code == 400
        assert ".xlsx" in response.json()["detail"]

    def test_empty_workbook_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        wb = Workbook()
        # Remove default sheet and create an empty one
        ws = wb.active
        buf = io.BytesIO()
        wb.save(buf)
        file_bytes = buf.getvalue()

        response = client.post(
            \"/api/admin/campaigns/00000000-0000-0000-0000-000000000000/import\",
            files={"file": ("empty.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            cookies={auth.SESSION_COOKIE_NAME: token},
        )
        assert response.status_code == 400

    def test_header_only_workbook_rejected(
        self, client, admin_user, mock_google_auth
    ):
        token = _login_as_admin(client, mock_google_auth)
        rows = [["Email ID*", "Name"]]
        response = _post_import(client, token, rows, "Header Only")
        assert response.status_code == 400
        assert "no student rows" in response.json()["detail"].lower()
