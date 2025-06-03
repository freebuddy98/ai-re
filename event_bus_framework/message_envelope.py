from typing import Optional, Dict, Any
from pydantic import BaseModel

class EventEnvelope(BaseModel):
    event_id: str
    event_type: str
    source_service: str
    published_at_utc: str
    version: str
    actual_payload: Dict[str, Any]
    trace_id: Optional[str] = None
    dialogue_session_id: Optional[str] = None 