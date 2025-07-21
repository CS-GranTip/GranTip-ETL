# db/models/criterion/general_criterion.py
from sqlalchemy import Column, Integer, String, ForeignKey
from db.database import Base
import json

class GeneralCriterion(Base):
    __tablename__ = "general_criterion"
    __table_args__ = {'extend_existing': True}  # 이 줄 추가!
    
    id = Column(Integer, primary_key=True, index=True)
    scholarship_id = Column(Integer, ForeignKey("scholarship.id"), comment="Scholarship ID (PK, FK)")
    
    required_qualifications = Column(String(500), comment="장학금 지원을 위한 필수 자격 조건 목록 (JSON 문자열로 저장)")
    preference_qualifications = Column(String(500), comment="우대 조건 목록 (JSON 문자열로 저장)")