from pydantic import BaseModel, Field

class ScholarshipRegion(BaseModel):
    scholarship_id: int = Field(..., description="Scholarship ID(FK)")
    region_id: int