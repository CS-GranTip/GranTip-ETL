from typing import Optional
from pydantic import BaseModel, Field
from enums import GradeCriterionType, ThresholdDirection

class GradeCriterion(BaseModel):
    scholarship_id: int = Field(..., description="Scholarship ID(FK)")
    group: str = Field(..., description="대상 그룹 (예: '신입생', '재학생')")
    type: GradeCriterionType = Field(..., description="기준 종류")

    # 아래 필드는 type 에 따라 사용
    score: Optional[float] = Field(None, description="GPA나 백분위 점수 등")
    max_score: Optional[float] = Field(None, description="GPA 만점 기준")
    credits: Optional[int]   = Field(None, description="이수학점 기준")
    rank: Optional[float]    = Field(None, description="석차/등급")
    unit: Optional[str]      = Field(None, description="단위 (등급, %, 점수 등)")
    keyword: Optional[str]   = Field(None, description="ETC 키워드 기준")
    direction: ThresholdDirection = Field(
        ThresholdDirection.NONE, description="기준 방향"
    )
    description: Optional[str]    = Field(None, description="원본 텍스트")

    class Config:
        orm_mode = True
        use_enum_values = True