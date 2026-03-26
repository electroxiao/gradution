from datetime import datetime

from pydantic import BaseModel


class WeakPointResponse(BaseModel):
    id: int
    node_name: str
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
