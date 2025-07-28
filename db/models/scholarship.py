# db/models/scholarship.py
from sqlalchemy import Column, Integer, BIGINT, String, Date, Boolean, JSON, TIMESTAMP, text
from sqlalchemy.orm import relationship
from .university_category import scholarship_university_category_table
from db.database import Base

class Scholarship(Base):
    __tablename__ = "scholarship"
    __table_args__ = {'extend_existing': True}  # 이 줄 추가!
    
    id = Column(BIGINT, primary_key=True, index=True, comment="시스템 내부 고유 ID (PK)")
    original_id = Column(BIGINT, unique=True, comment="운영기관이 제공한 원본 번호")
    product_name = Column(String(255))
    provider_name = Column(String(255))
    provider_type = Column(String(100), comment="Enum 문자열로 저장")
    product_type = Column(String(100), comment="Enum 문자열로 저장")
    scholarship_category = Column(String(100), comment="Enum 문자열로 저장")
    application_start_date = Column(Date)
    application_end_date = Column(Date)
    homepage_url = Column(String(500), nullable=True)
    university_categories = relationship(
        "UniversityCategory",
        secondary=scholarship_university_category_table,
        back_populates="scholarships"
    )
    grade_category = Column(JSON, comment="학년 구분 (JSON으로 저장)")
    department_category = Column(JSON, comment="학과 구분 (JSON으로 저장)")
    num_of_recipients_total = Column(Integer, nullable=True, comment="총 선발 인원")
    recipients_by_category = Column(JSON, nullable=True, comment="구분별 선발 인원 (JSON으로 저장)")
    is_recommendation_required = Column(Boolean, comment="추천서 필요 여부")
    is_duplicate_support_restricted = Column(Boolean, comment="중복 수혜 제한 여부")
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

    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))