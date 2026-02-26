from typing import Optional, Literal
from pydantic import BaseModel

Status = Literal["queued", "running", "done", "failed"]

class StatusResponse(BaseModel):
    task_id: str
    status: Status
    error: Optional[str] = None
    result: Optional[dict] = None