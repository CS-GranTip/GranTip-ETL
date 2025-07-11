from typing   import Optional
from pydantic import BaseModel, Field

class IncomeCriterion(BaseModel):
    scholarship_id: int = Field(..., description="Scholarship ID(FK)")

    # --- 장학금 소득 기준 값들 ---
    scholarship_support_interval: Optional[int] = Field(None, description="한국장학재단 학자금 지원구간 (1~9구간)")
    income_percentile_band: Optional[int] = Field(None, description="소득분위 (1~8분위). 'n 분위 이내'라면 n")
    median_income_ratio: Optional[int] = Field(None, description="기준 중위소득 비율 (%)")

    # --- 특수 계층 플래그 (우선/대상 조건) ---
    disabled:             bool = Field(False, description="장애인 대상 여부")
    multi_child:          bool = Field(False, description="다자녀 가정 대상 여부")
    national_merit:       bool = Field(False, description="국가유공자/보훈자 대상 여부")
    single_parent:        bool = Field(False, description="한부모 가정 대상 여부")
    orphan:               bool = Field(False, description="소년소녀가장 대상 여부")
    low_income:           bool = Field(False, description="저소득층 대상 여부")
    multicultural:        bool = Field(False, description="다문화 가정 대상 여부")
    north_korean_defector: bool = Field(False, description="북한이탈주민 대상 여부")

    class Config:
        orm_mode = True
        use_enum_values = True