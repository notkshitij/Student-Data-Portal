"""
Schemas for Excel import.
"""

import uuid

from pydantic import BaseModel, ConfigDict


class ImportResponse(BaseModel):
    """Response returned after successfully importing a campaign."""

    model_config = ConfigDict(from_attributes=True)

    campaign_id: uuid.UUID
    import_id: uuid.UUID
    campaign_name: str
    status: str
    num_students: int
    num_fields: int
    num_collect_cells: int
    fields_discovered: list[str]
    fields_with_collect: list[str]
    rows_processed: int
    rejected_rows: int
