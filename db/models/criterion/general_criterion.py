# db/models/criterion/general_criterion.py
from sqlalchemy import Column, Integer, ForeignKey, TEXT, TIMESTAMP, text
from db.database import Base
import json

class GeneralCriterion(Base):
    __tablename__ = "general_criterion"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    scholarship_id = Column(Integer, ForeignKey("scholarship.id"), comment="Scholarship ID (PK, FK)")
    
    required_qualifications = Column(TEXT, comment="장학금 지원을 위한 필수 자격 조건 목록 (JSON 문자열로 저장)")
    preference_qualifications = Column(TEXT, comment="우대 조건 목록 (JSON 문자열로 저장)")

    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))