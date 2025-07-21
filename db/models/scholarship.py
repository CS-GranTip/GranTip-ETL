# db/models/scholarship.py
from sqlalchemy import Column, Integer, String, Date, Boolean
from db.database import Base
import json

class Scholarship(Base):
    __tablename__ = "scholarship"
    __table_args__ = {'extend_existing': True}  # 이 줄 추가!
    
    id = Column(Integer, primary_key=True, index=True, comment="시스템 내부 고유 ID (PK)")
    original_id = Column(Integer, unique=True, comment="운영기관이 제공한 원본 번호")
    product_name = Column(String(255))
    provider_name = Column(String(255))
    provider_type = Column(String(100), comment="Enum 문자열로 저장")
    product_type = Column(String(100), comment="Enum 문자열로 저장")
    scholarship_category = Column(String(100), comment="Enum 문자열로 저장")
    application_start_date = Column(Date)
    application_end_date = Column(Date)
    homepage_url = Column(String(500), nullable=True)
    university_category = Column(String(500), comment="대학 구분 (JSON 문자열로 저장)")
    grade_category = Column(String(500), comment="학년 구분 (JSON 문자열로 저장)")
    department_category = Column(String(500), comment="학과 구분 (JSON 문자열로 저장)")
    num_of_recipients_total = Column(Integer, nullable=True, comment="총 선발 인원")
    recipients_by_category = Column(String(500), nullable=True, comment="구분별 선발 인원 (JSON 문자열로 저장)")
    is_recommendation_required = Column(Boolean, comment="추천서 필요 여부")
    is_duplicate_support_restricted = Column(Boolean, comment="중복 수혜 제한 여부")
    qualification_tags = Column(String(500), comment="자격 키워드 태그 (JSON 문자열로 저장)")
    grade_criteria_detail = Column(String(500), nullable=True)
    income_criteria_detail = Column(String(500), nullable=True)
    support_detail = Column(String(500), nullable=True)
    specific_qualification_detail = Column(String(500), nullable=True)
    region_residence_detail = Column(String(500), nullable=True)
    selection_method_detail = Column(String(500), nullable=True)
    selection_personnel_detail = Column(String(500), nullable=True)
    qualification_restriction_detail = Column(String(500), nullable=True)
    recommendation_needed_detail = Column(String(500), nullable=True)
    required_documents_detail = Column(String(500), nullable=True)
    grade_criteria_notes = Column(String(500), nullable=True)
    income_criteria_notes = Column(String(500), nullable=True)
    support_notes = Column(String(500), nullable=True)
    specific_qualification_notes = Column(String(500), nullable=True)
    region_residence_notes = Column(String(500), nullable=True)
    selection_method_notes = Column(String(500), nullable=True)
    selection_personnel_notes = Column(String(500), nullable=True)
    qualification_restriction_notes = Column(String(500), nullable=True)
    recommendation_needed_notes = Column(String(500), nullable=True)
    required_documents_notes = Column(String(500), nullable=True)