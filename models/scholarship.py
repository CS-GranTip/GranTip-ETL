from datetime import date
from typing     import Optional, List, Dict
from pydantic   import BaseModel, Field, HttpUrl, ConfigDict
from enums      import (
    ProviderType,
    ProductType,
    ScholarshipCategory
)
from models.criterion.grade_criterion import GradeCriterion
from models.criterion.income_criterion import IncomeCriterion

class Scholarship(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra='ignore', use_enum_values=True)

    # --- 필수 정보 ---
    id: int                     = Field(..., alias="번호")
    product_name: str           = Field(..., alias="상품명")
    provider_name: str          = Field(..., alias="운영기관명")
    provider_type: ProviderType = Field(..., alias="운영기관구분")
    product_type: ProductType   = Field(..., alias="상품구분")
    scholarship_category: ScholarshipCategory = Field(..., alias="학자금유형구분")

    # --- 날짜 및 URL 정보 ---
    application_start_date: date     = Field(..., alias="모집시작일")
    application_end_date:   date     = Field(..., alias="모집종료일")
    homepage_url:            HttpUrl = Field(None, alias="홈페이지 주소")

    # --- 가공된 분류 목록 ---
    university_category: List[str] = Field(default_factory=list, description="대학 구분")
    grade_category:      List[str] = Field(default_factory=list, description="학년 구분")
    department_category: List[str] = Field(default_factory=list, description="학과 구분")

    # --- 선발 인원 정보 ---
    num_of_recipients_total: Optional[int]           = Field(None, description="총 선발 인원")
    recipients_by_category:  Optional[Dict[str,int]] = Field(None, description="구분별 선발 인원")
    num_notes: Optional[str]                         = Field(None, description="선발 인원 비고")

    # --- 분리된 성적 기준 ---
    grade_criteria:       List[GradeCriterion]  = Field(default_factory=list, description="분리된 성적 기준 리스트")

    # --- 분리된 소득 기준 ---
    income_criteria:       List[IncomeCriterion] = Field(default_factory=list, description="분리된 소득 기준 리스트")

    # --- 기타 정보 ---
    is_recommendation_required:    bool      = Field(False, description="추천서 필요 여부")
    is_duplicate_support_restricted: bool    = Field(False, description="중복 수혜 제한 여부")
    qualification_tags:            List[str] = Field(default_factory=list, description="자격 키워드 태그") # 뺄지말지

    # --- 원본 텍스트 ---
    grade_criteria_detail: Optional[str] = Field(None, alias="성적기준 상세내용")
    income_criteria_detail: Optional[str] = Field(None, alias="소득기준 상세내용")
    support_detail: Optional[str] = Field(None, alias="지원내역 상세내용")
    specific_qualification_detail: Optional[str] = Field(None, alias="특정자격 상세내용")
    region_residence_detail: Optional[str] = Field(None, alias="지역거주여부 상세내용")
    selection_method_detail: Optional[str] = Field(None, alias="선발방법 상세내용")
    selection_personnel_detail: Optional[str] = Field(None, alias="선발인원 상세내용")
    qualification_restriction_detail: Optional[str] = Field(None, alias="자격제한 상세내용")
    recommendation_needed_detail: Optional[str] = Field(None, alias="추천필요여부 상세내용")
    required_documents_detail: Optional[str] = Field(None, alias="제출서류 상세내용")


    # --- 비고 ---
    grade_criteria_notes: Optional[str] = Field(None, description="성적 기준 전체 비고")
    income_criteria_notes: Optional[str] = Field(None, description="소득 기준 전체 비고")
    support_notes: Optional[str] = Field(None, description="지원내역 전체 비고")
    specific_qualification_notes: Optional[str] = Field(None, description="특정자격 전체 비고")
    region_residence_notes: Optional[str] = Field(None, description="지역 거주 여부 전체 비고")
    selection_method_notes: Optional[str] = Field(None, description="선발방법 전체 비고")
    selection_personnel_notes: Optional[str] = Field(None, description="선발인원 전체 비고")
    qualification_restriction_notes: Optional[str] = Field(None, description="자격제한 전체 비고")
    recommendation_needed_notes: Optional[str] = Field(None, description="추천필요여부 전체 비고")
    required_documents_notes: Optional[str] = Field(None, description="제출서류 전체 비고")
