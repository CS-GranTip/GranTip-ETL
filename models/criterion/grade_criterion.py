from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from pathlib import Path
import sys
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from enums import GradeCriterionType, ThresholdDirection, BaseSemester

# grade_criterion.py에서 GradeCriterion 클래스 직접 정의
class GradeCriterion(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    scholarship_id: int = Field(..., description="Scholarship ID(FK)")
    group: str = Field(..., description="대상 그룹 (예: '신입생', '재학생')")
    type: GradeCriterionType = Field(..., description="기준 종류")

    # 아래 필드는 type 에 따라 사용
    score5: Optional[float] = Field(None, description="GPA(4.5점 만점)나 백분위 점수 등")
    score3: Optional[float] = Field(None, description="GPA(4.3점 만점)")
    credits: Optional[int]   = Field(None, description="이수학점 기준")
    rank: Optional[float]    = Field(None, description="석차/등급")
    unit: Optional[str]      = Field(None, description="단위 (등급, %, 점수 등)")
    keyword: Optional[str]   = Field(None, description="ETC 키워드 기준")
    direction: ThresholdDirection = Field(
        ThresholdDirection.NONE.value, description="기준 방향"
    )
    semester: BaseSemester = Field(
        BaseSemester.NONE.value, description="기준 학기"
    )
    description: Optional[str]    = Field(None, description="원본 텍스트")
    