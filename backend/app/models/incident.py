from pydantic import BaseModel, Field
from typing import List, Optional


class Incident(BaseModel):
    incident_id: str
    title: str
    service: str
    environment: str
    severity: str
    error_message: str
    description: str
    traffic: Optional[int] = None
    database: Optional[str] = None
    status: str = "open"

    root_cause: Optional[str] = None
    resolution: Optional[str] = None

    successful: Optional[bool] = None

    attempted_actions: List[str] = Field(default_factory=list)