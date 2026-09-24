"""
Schemas for Excel import.
"""

from pydantic import BaseModel, ConfigDict
import uuid

class ImportResponse(BaseModel):
    """Response returned after successfully importing a campaign."""
    model_config = ConfigDict(from_attributes=True)

    campaign_id: uuid.UUID
    num_students: int
    num_fields: int
    num_collect_cells: int
    status: str
