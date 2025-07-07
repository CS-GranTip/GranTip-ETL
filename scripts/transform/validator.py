from enum import Enum
from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl

class ProviderType(str, Enum):
    LOCAL_GOV = "지자체(출자출연기관)"
    PUBLIC_ORG = "공공기관"
    ETC = "기타"

class ProductType(str, Enum):
    SCHOLARSHIP = "장학금"
    LOAN = "학자금"

class ScholarshipCategory(str, Enum):
    LOCAL = "지역연고"
    SPECIALTY = "특기자"
    GRADE = "성적우수"
    INCOME = "소득구분"
    DISABILITY = "장애인"
    ETC = "기타"
    NONE = "해당없음"

class Scholarship(BaseModel):
    """DB에 저장될 최종 장학금 데이터의 스키마(규칙)를 정의합니다."""
    
    # --- 필수 정보 ---
    id: int = Field(..., alias="번호")
    product_name: str = Field(..., alias="상품명")
    provider_name: str = Field(..., alias="운영기관명")
    provider_type: ProviderType = Field(..., alias="운영기관구분")
    product_type: ProductType = Field(..., alias="상품구분")
    scholarship_category: ScholarshipCategory = Field(..., alias="학자금유형구분")

    # --- 날짜 및 URL 정보 ---
    application_start_date: date = Field(..., alias="모집시작일")
    application_end_date: date = Field(..., alias="모집종료일")
    homepage_url: Optional[HttpUrl] = Field(None, alias="홈페이지 주소")

    # --- 원본 텍스트 가공하여 채울 구조화된 필드 ---

    # 가공 후 List[str] 정보
    university_category: List[str] = Field(default_factory=list, description="대학 구분 목록 (처리 후)")
    grade_category: List[str] = Field(default_factory=list, description="학년 구분 목록 (처리 후)")
    department_category: List[str] = Field(default_factory=list, description="학과 구분 목록 (처리 후)")

    # '지원내역 상세내용'에서 추출
    
    # '선발인원 상세내용'에서 추출
    num_of_recipients_total: Optional[int] = Field(None, description="총 선발 인원(숫자). '12명' -> 12")
    recipients_by_category: Optional[Dict[str, int]] = Field(None, description="구분별 선발 인원. '4년제 36명' -> {'4년제': 36}")
    num_notes: Optional[str] = Field(None, description="선발 인원 관련 비고 (예: 약간 명, 각 학교당 1명)")

    # '성적기준 상세내용'에서 추출
    
    # '추천필요여부 상세내용'에서 추출
    is_recommendation_required: bool = Field(False, description="추천서 필요 여부")

    # '자격제한 상세내용'에서 추출
    is_duplicate_support_restricted: bool = Field(False, description="타 장학금 중복수혜 제한 여부")
    
    # '특정자격 상세내용', '자격제한 상세내용' 등에서 키워드 추출
    qualification_tags: List[str] = Field(default_factory=list, description="자격 요건 키워드 태그 (예: ['다문화', '경영학과'])")


    # --- 참고용 원본 텍스트 필드 (추후 필요 여부 확인 후 삭제 가능) ---
    university_category_str: Optional[str] = Field(None, alias="대학구분")
    grade_category_str: Optional[str] = Field(None, alias="학년구분")
    department_category_str: Optional[str] = Field(None, alias="학과구분")
    grade_criteria_detail: Optional[str] = Field(None, alias="성적기준 상세내용")
    income_criteria_detail: Optional[str] = Field(None, alias="소득기준 상세내용")
    support_detail: Optional[str] = Field(None, alias="지원내역 상세내용")
    specific_qualification_detail: Optional[str] = Field(None, alias="특정자격 상세내용")
    residence_requirement_detail: Optional[str] = Field(None, alias="지역거주여부 상세내용")
    selection_method_detail: Optional[str] = Field(None, alias="선발방법 상세내용")
    selection_personnel_detail: Optional[str] = Field(None, alias="선발인원 상세내용")
    qualification_restriction_detail: Optional[str] = Field(None, alias="자격제한 상세내용")
    recommendation_needed_detail: Optional[str] = Field(None, alias="추천필요여부 상세내용")
    required_documents_detail: Optional[str] = Field(None, alias="제출서류 상세내용")

    

    class Config:
        populate_by_name = True # alias를 기준으로 데이터를 받음
        extra = 'ignore'      # 모델에 정의되지 않은 추가 필드는 무시
        use_enum_values = True  # Enum 값을 기준으로 데이터를 처리

# 이 파일은 다른 파일에서 import하여 사용됩니다.
if __name__ == "__main__":
    # 샘플 데이터
    sample_data = {
        "title": "기본 장학금",
        "provider": "기본 재단",
        "amount": 1000000,
        "end_date": "2025-09-30"
    }
    
    # 샘플 데이터로 모델 인스턴스 생성
    scholarship_instance = Scholarship(**sample_data)
    
    # 생성된 인스턴스 출력
    print("Pydantic 모델 테스트 성공:")
    print(scholarship_instance)