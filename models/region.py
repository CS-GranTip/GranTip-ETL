from typing import Optional
from pydantic import BaseModel

class Region(BaseModel):
    id: int
    parent_id: Optional[int] = None
    region_name: str
    region_level: int