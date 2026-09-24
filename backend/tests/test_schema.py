"""
Tests for the core application database schema.

Covers the key relationships and constraints specified in the design:
1. Duplicate campaign membership is rejected.
2. A student can belong to multiple campaigns.
3. Different students can have different requires_student_input values for the same field.
4. Student responses do not overwrite original imported values.
5. Foreign keys and uniqueness constraints work correctly.
6. Campaign field uniqueness within a campaign.
7. Imported field value uniqueness per student per field.
"""

import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.session import Base
from app.models import (
    AuditLog,
    Campaign,
    CampaignField,
    CampaignStatus,
    CampaignStudent,
    CampaignSubmission,
    Import,
    ImportedFieldValue,
    ImportStatus,
    StudentResponse,
    SubmissionStatus,
    SystemMetadata,
    User,
    UserRole,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    """Create a SQLAlchemy engine for the test database."""
    eng = create_engine(settings.database_url, pool_pre_ping=True)
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def tables_exist(engine):
    """Verify all expected tables exist before running tests."""
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    expected = {
        "users",
        "campaigns",
        "campaign_students",
        "campaign_fields",
        "imported_field_values",
        "student_responses",
        "campaign_submissions",
        "imports",
        "audit_logs",
        "system_metadata",
    }
    missing = expected - existing
    assert not missing, f"Missing tables: {missing}"
    return True


@pytest.fixture()
def db(engine, tables_exist):
    """Provide a transactional session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_admin(db: Session, email: str = "admin@test.com") -> User:
    """Create and flush an ADMIN user."""
    user = User(email=email, role=UserRole.ADMIN, google_subject_id=f"sub_{email}")
    db.add(user)
    db.flush()
    return user


def _make_student(db: Session, email: str = "student@test.com") -> User:
    """Create and flush a STUDENT user."""
    user = User(email=email, role=UserRole.STUDENT)
    db.add(user)
    db.flush()
    return user


def _make_campaign(db: Session, admin: User, name: str = "Campaign 1") -> Campaign:
    """Create and flush a campaign."""
    campaign = Campaign(
        name=name,
        status=CampaignStatus.DRAFT,
        created_by_id=admin.id,
    )
    db.add(campaign)
    db.flush()
    return campaign


def _make_field(
    db: Session, campaign: Campaign, name: str, order: int = 0,
) -> CampaignField:
    """Create and flush a campaign field."""
    field = CampaignField(
        campaign_id=campaign.id,
        field_name=name,
        field_order=order,
    )
    db.add(field)
    db.flush()
    return field


def _make_membership(
    db: Session, campaign: Campaign, student: User,
) -> CampaignStudent:
    """Create and flush a campaign–student membership."""
    cs = CampaignStudent(
        campaign_id=campaign.id,
        student_id=student.id,
    )
    db.add(cs)
    db.flush()
    return cs


def _make_imported_value(
    db: Session,
    cs: CampaignStudent,
    field: CampaignField,
    value: str | None,
    requires_input: bool = False,
) -> ImportedFieldValue:
    """Create and flush an imported field value."""
    ifv = ImportedFieldValue(
        campaign_student_id=cs.id,
        campaign_field_id=field.id,
        imported_value=value,
        requires_student_input=requires_input,
    )
    db.add(ifv)
    db.flush()
    return ifv


# ---------------------------------------------------------------------------
# Test 1: Duplicate campaign membership is rejected
# ---------------------------------------------------------------------------


class TestDuplicateMembership:
    """A student cannot be added twice to the same campaign."""

    def test_duplicate_campaign_student_raises(self, db: Session):
        admin = _make_admin(db)
        student = _make_student(db)
        campaign = _make_campaign(db, admin)

        _make_membership(db, campaign, student)

        duplicate = CampaignStudent(
            campaign_id=campaign.id,
            student_id=student.id,
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.flush()


# ---------------------------------------------------------------------------
# Test 2: A student can belong to multiple campaigns
# ---------------------------------------------------------------------------


class TestMultipleCampaignMembership:
    """A single student can participate in different campaigns."""

    def test_student_in_multiple_campaigns(self, db: Session):
        admin = _make_admin(db)
        student = _make_student(db)
        campaign_a = _make_campaign(db, admin, name="Campaign A")
        campaign_b = _make_campaign(db, admin, name="Campaign B")

        cs_a = _make_membership(db, campaign_a, student)
        cs_b = _make_membership(db, campaign_b, student)

        assert cs_a.campaign_id == campaign_a.id
        assert cs_b.campaign_id == campaign_b.id
        assert cs_a.student_id == cs_b.student_id == student.id


# ---------------------------------------------------------------------------
# Test 3: Different requires_student_input per student for the same field
# ---------------------------------------------------------------------------


class TestDifferentCollectFlags:
    """Different students can have different requires_student_input values
    for the same campaign field — this is the core [COLLECT] mechanism."""

    def test_different_requires_input_for_same_field(self, db: Session):
        admin = _make_admin(db)
        student_a = _make_student(db, email="a@test.com")
        student_b = _make_student(db, email="b@test.com")
        campaign = _make_campaign(db, admin)
        phone_field = _make_field(db, campaign, "Phone")

        cs_a = _make_membership(db, campaign, student_a)
        cs_b = _make_membership(db, campaign, student_b)

        # Student A has phone → read-only
        ifv_a = _make_imported_value(
            db, cs_a, phone_field, "9876543210", requires_input=False,
        )
        # Student B needs to provide phone → [COLLECT]
        ifv_b = _make_imported_value(
            db, cs_b, phone_field, None, requires_input=True,
        )

        assert ifv_a.requires_student_input is False
        assert ifv_a.imported_value == "9876543210"
        assert ifv_b.requires_student_input is True
        assert ifv_b.imported_value is None


# ---------------------------------------------------------------------------
# Test 4: Student responses do not overwrite original imported values
# ---------------------------------------------------------------------------


class TestResponsesPreserveImportedValues:
    """Submitting a student response must never change the imported value."""

    def test_response_stored_separately(self, db: Session):
        admin = _make_admin(db)
        student = _make_student(db)
        campaign = _make_campaign(db, admin)
        dob_field = _make_field(db, campaign, "DOB")
        cs = _make_membership(db, campaign, student)

        # Import with [COLLECT] marker
        ifv = _make_imported_value(db, cs, dob_field, None, requires_input=True)

        # Student responds
        response = StudentResponse(
            imported_field_value_id=ifv.id,
            response_value="15/06/2004",
        )
        db.add(response)
        db.flush()

        # Verify the imported value is untouched
        db.refresh(ifv)
        assert ifv.imported_value is None  # Still None — never overwritten
        assert response.response_value == "15/06/2004"

    def test_response_references_correct_imported_value(self, db: Session):
        admin = _make_admin(db)
        student = _make_student(db, email="ref@test.com")
        campaign = _make_campaign(db, admin)
        field = _make_field(db, campaign, "Name")
        cs = _make_membership(db, campaign, student)
        ifv = _make_imported_value(db, cs, field, "Rahul", requires_input=False)

        response = StudentResponse(
            imported_field_value_id=ifv.id,
            response_value="Rahul Kumar",
        )
        db.add(response)
        db.flush()

        # The response links back to the correct imported field value
        assert response.imported_field_value_id == ifv.id
        # Original value is preserved
        db.refresh(ifv)
        assert ifv.imported_value == "Rahul"


# ---------------------------------------------------------------------------
# Test 5: Foreign keys and uniqueness constraints
# ---------------------------------------------------------------------------


class TestForeignKeysAndConstraints:
    """Foreign keys and uniqueness constraints are enforced."""

    def test_campaign_requires_valid_creator(self, db: Session):
        """Campaign creation with a non-existent user ID should fail."""
        campaign = Campaign(
            name="Orphan",
            status=CampaignStatus.DRAFT,
            created_by_id=uuid.uuid4(),  # doesn't exist
        )
        db.add(campaign)
        with pytest.raises(IntegrityError):
            db.flush()

    def test_imported_value_requires_valid_campaign_student(self, db: Session):
        """ImportedFieldValue with non-existent campaign_student_id should fail."""
        admin = _make_admin(db, email="fk_admin@test.com")
        campaign = _make_campaign(db, admin)
        field = _make_field(db, campaign, "Email")

        ifv = ImportedFieldValue(
            campaign_student_id=uuid.uuid4(),  # doesn't exist
            campaign_field_id=field.id,
            imported_value="test@example.com",
        )
        db.add(ifv)
        with pytest.raises(IntegrityError):
            db.flush()

    def test_duplicate_field_name_in_same_campaign_rejected(self, db: Session):
        """Two fields with the same name in the same campaign should fail."""
        admin = _make_admin(db, email="dup_field@test.com")
        campaign = _make_campaign(db, admin)
        _make_field(db, campaign, "Phone")

        duplicate = CampaignField(
            campaign_id=campaign.id,
            field_name="Phone",
            field_order=1,
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.flush()

    def test_same_field_name_in_different_campaigns_allowed(self, db: Session):
        """Two different campaigns can have fields with the same name."""
        admin = _make_admin(db, email="multi_camp@test.com")
        campaign_a = _make_campaign(db, admin, name="C-A")
        campaign_b = _make_campaign(db, admin, name="C-B")

        field_a = _make_field(db, campaign_a, "Phone")
        field_b = _make_field(db, campaign_b, "Phone")

        assert field_a.field_name == field_b.field_name
        assert field_a.campaign_id != field_b.campaign_id

    def test_duplicate_imported_value_for_same_student_field_rejected(
        self, db: Session,
    ):
        """A student cannot have two imported values for the same field."""
        admin = _make_admin(db, email="dup_ifv@test.com")
        student = _make_student(db, email="dup_ifv_student@test.com")
        campaign = _make_campaign(db, admin)
        field = _make_field(db, campaign, "Name")
        cs = _make_membership(db, campaign, student)

        _make_imported_value(db, cs, field, "Rahul")

        duplicate = ImportedFieldValue(
            campaign_student_id=cs.id,
            campaign_field_id=field.id,
            imported_value="Another",
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.flush()

    def test_unique_email_constraint(self, db: Session):
        """Two users cannot have the same email."""
        _make_student(db, email="unique@test.com")
        duplicate = User(email="unique@test.com", role=UserRole.STUDENT)
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.flush()

    def test_duplicate_student_response_for_same_field_rejected(self, db: Session):
        """Only one response per imported field value."""
        admin = _make_admin(db, email="dup_resp@test.com")
        student = _make_student(db, email="dup_resp_s@test.com")
        campaign = _make_campaign(db, admin)
        field = _make_field(db, campaign, "Phone")
        cs = _make_membership(db, campaign, student)
        ifv = _make_imported_value(db, cs, field, None, requires_input=True)

        resp_1 = StudentResponse(
            imported_field_value_id=ifv.id,
            response_value="123",
        )
        db.add(resp_1)
        db.flush()

        resp_2 = StudentResponse(
            imported_field_value_id=ifv.id,
            response_value="456",
        )
        db.add(resp_2)
        with pytest.raises(IntegrityError):
            db.flush()


# ---------------------------------------------------------------------------
# Test 6: Campaign status and submission workflow
# ---------------------------------------------------------------------------


class TestCampaignWorkflow:
    """Campaign lifecycle and student submission status."""

    def test_campaign_default_status_is_draft(self, db: Session):
        admin = _make_admin(db, email="draft_admin@test.com")
        campaign = _make_campaign(db, admin)
        assert campaign.status == CampaignStatus.DRAFT

    def test_campaign_student_default_status_is_pending(self, db: Session):
        admin = _make_admin(db, email="pending_admin@test.com")
        student = _make_student(db, email="pending_student@test.com")
        campaign = _make_campaign(db, admin)
        cs = _make_membership(db, campaign, student)
        assert cs.status == SubmissionStatus.PENDING

    def test_submission_records_are_created(self, db: Session):
        admin = _make_admin(db, email="sub_admin@test.com")
        student = _make_student(db, email="sub_student@test.com")
        campaign = _make_campaign(db, admin)
        cs = _make_membership(db, campaign, student)

        submission = CampaignSubmission(campaign_student_id=cs.id)
        db.add(submission)
        db.flush()

        assert submission.campaign_student_id == cs.id
        assert submission.submitted_at is not None


# ---------------------------------------------------------------------------
# Test 7: Import and audit log models
# ---------------------------------------------------------------------------


class TestImportAndAudit:
    """Import metadata and audit logging."""

    def test_import_record_created(self, db: Session):
        admin = _make_admin(db, email="import_admin@test.com")
        campaign = _make_campaign(db, admin)

        imp = Import(
            campaign_id=campaign.id,
            uploaded_by_id=admin.id,
            original_filename="students.xlsx",
            row_count=100,
            status=ImportStatus.COMPLETED,
        )
        db.add(imp)
        db.flush()

        assert imp.original_filename == "students.xlsx"
        assert imp.row_count == 100
        assert imp.status == ImportStatus.COMPLETED

    def test_audit_log_created(self, db: Session):
        admin = _make_admin(db, email="audit_admin@test.com")

        log = AuditLog(
            user_id=admin.id,
            action="CREATE_CAMPAIGN",
            entity_type="Campaign",
            entity_id=str(uuid.uuid4()),
            details={"name": "Test Campaign"},
        )
        db.add(log)
        db.flush()

        assert log.action == "CREATE_CAMPAIGN"
        assert log.details["name"] == "Test Campaign"

    def test_audit_log_without_user(self, db: Session):
        """Audit logs can have null user_id for system events."""
        log = AuditLog(
            user_id=None,
            action="SYSTEM_STARTUP",
            entity_type="System",
            entity_id="system",
        )
        db.add(log)
        db.flush()

        assert log.user_id is None


# ---------------------------------------------------------------------------
# Test 8: All expected tables exist
# ---------------------------------------------------------------------------


class TestTableExistence:
    """All tables from the schema must exist in the database."""

    def test_all_tables_present(self, engine, tables_exist):
        """Validated by the tables_exist fixture."""
        assert tables_exist is True
