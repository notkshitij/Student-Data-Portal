"""
Models package.

All model modules are imported here so that Base.metadata is fully
populated when Alembic runs autogenerate.
"""

from app.models.system_metadata import SystemMetadata
from app.models.user import User, UserRole
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_student import CampaignStudent, SubmissionStatus
from app.models.campaign_field import CampaignField
from app.models.imported_field_value import ImportedFieldValue
from app.models.student_response import StudentResponse
from app.models.campaign_submission import CampaignSubmission
from app.models.import_record import Import, ImportStatus
from app.models.audit_log import AuditLog
from app.models.user_session import UserSession

__all__ = [
    "SystemMetadata",
    "User",
    "UserRole",
    "Campaign",
    "CampaignStatus",
    "CampaignStudent",
    "SubmissionStatus",
    "CampaignField",
    "ImportedFieldValue",
    "StudentResponse",
    "CampaignSubmission",
    "Import",
    "ImportStatus",
    "AuditLog",
    "UserSession",
]
