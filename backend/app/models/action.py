from pydantic import BaseModel, Field
from typing import Optional


class IncidentAction(BaseModel):
    action: str = Field(..., min_length=1)
    result: str = Field(..., pattern="^(success|failed)$")
    reason: Optional[str] = None