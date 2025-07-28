# db/models/criterion/income_criterion.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP, text
from db.database import Base
import json

class IncomeCriterion(Base):
    __tablename__ = "income_criterion"
    __table_args__ = {'extend_existing': True}  # 이 줄 추가!
    
    id = Column(Integer, primary_key=True, index=True)
    scholarship_id = Column(Integer, ForeignKey("scholarship.id"), comment="Scholarship ID(FK)")
    priority = Column(Integer, comment="규칙 적용 우선순위 (낮을수록 높음)")
    description = Column(String(500), nullable=True, comment="규칙에 대한 설명")
    aid_type = Column(String(100), nullable=True, comment="규칙이 적용되는 지원금 종류 (Enum 문자열로 저장)")
    
    required_qualifications = Column(String(500), comment="규칙 적용에 필요한 필수 자격 조건 목록 (JSON 문자열로 저장)")
    preference_qualifications = Column(String(500), comment="우대 조건 목록 (JSON 문자열로 저장)")
    
    ignore_income_and_assets = Column(Boolean, comment="소득/재산 기준 면제 여부")
    
    scholarship_support_interval = Column(Integer, nullable=True, comment="한국장학재단 학자금 지원구간 (n구간 이하)")
    income_percentile_band = Column(Integer, nullable=True, comment="소득분위 (n분위 이내)")
    median_income_ratio = Column(Integer, nullable=True, comment="기준 중위소득 비율 (n% 이하)")

    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))