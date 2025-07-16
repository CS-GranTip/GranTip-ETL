from pydantic import BaseModel, Field, ConfigDict
from typing import List
from enums import QualificationCode

class GeneralCriterion(BaseModel):
    """
    장학금의 '최소 지원 자격'
    장학금과 1:1 관계
    이 조건을 만족해야만 다음 단계인 소득 심사를 진행
    """
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    scholarship_id: int = Field(..., description="Scholarship ID (PK, FK)")
    
    required_qualifications: List[QualificationCode] = Field(
        default_factory=list,
        description="장학금 지원을 위한 필수 자격 조건 목록"
    )
    preference_qualifications: List[QualificationCode] = Field(
        default_factory=list,
        description="우대 조건 목록"
    )