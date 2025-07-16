from typing   import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from enums import QualificationCode, AidType

class IncomeCriterion(BaseModel):
    """
    '조건부 소득 규칙' 정의 
    장학금과 1:N 관계
    하나의 장학금은 여러 개의 소득 규칙을 가질 수 있음
    """
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    # --- 기본 정보 ---
    # DB에서 자동 생성되므로 Python에서 생성할 때는 값이 없어도 됨 (None)
    id: Optional[int] = Field(None, description="규칙의 고유 ID (PK)")
    scholarship_id: int = Field(..., description="Scholarship ID(FK)")
    priority: int = Field(1, description="규칙 적용 우선순위 (낮을수록 높음)")
    description: Optional[str] = Field(None, description="규칙에 대한 설명 (예: '다자녀 특별 전형', '재학생 생활비 기준')")

    aid_type: Optional[AidType] = Field(None, description="규칙이 적용되는 지원금 종류 (학자금/생활비)")

    # --- 조건부 자격 ---
    # 이 규칙이 적용되기 위해 사용자가 '반드시' 충족해야 하는 조건 목록
    # 빈 리스트 []는 모든 사용자에게 적용되는 기본 규칙임을 의미
    # 예: ['MULTI_CHILD'], ['FRESHMAN'], ['LIVING_IN_SEOUL', 'DISABLED']
    required_qualifications: List[QualificationCode] = Field(
        default_factory=list,
        description="규칙 적용에 필요한 필수 자격 조건 목록"
    )
    preference_qualifications: List[QualificationCode] = Field(
        default_factory=list,
        description="우대 조건 목록"
    )

    # --- 소득 기준 면제 ---
    # 이 규칙에 해당하면 소득/재산 기준을 아예 무시할지 여부
    # 예: 다자녀는 소득 무관 -> required_qualifications=['MULTI_CHILD'], ignore_income_and_assets=True
    ignore_income_and_assets: bool = Field(False, description="소득/재산 기준 면제 여부")

    # --- 정량적 소득/재산 기준 ---
    # ignore_income_and_assets가 False일 때 사용되는 값들
    scholarship_support_interval: Optional[int] = Field(None, description="한국장학재단 학자금 지원구간 (n구간 이하)")
    income_percentile_band: Optional[int] = Field(None, description="소득분위 (n분위 이내)")
    median_income_ratio: Optional[int] = Field(None, description="기준 중위소득 비율 (n% 이하)")
    