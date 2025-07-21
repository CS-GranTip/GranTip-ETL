# db/models/criterion/grade_criterion.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, TEXT
from db.database import Base

class GradeCriterion(Base):
    __tablename__ = "grade_criterion"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    scholarship_id = Column(Integer, ForeignKey("scholarship.id"), comment="Scholarship ID(FK)")
    group = Column(String(100), comment="대상 그룹 (예: '신입생', '재학생')")
    type = Column(String(100), comment="기준 종류 (Enum 문자열로 저장)")
    
    score5 = Column(Float, nullable=True, comment="GPA(4.5점 만점)나 백분위 점수 등")
    score3 = Column(Float, nullable=True, comment="GPA(4.3점 만점)")
    credits = Column(Integer, nullable=True, comment="이수학점 기준")
    rank = Column(Float, nullable=True, comment="석차/등급")
    unit = Column(String(50), nullable=True, comment="단위 (등급, %, 점수 등)")
    keyword = Column(String(255), nullable=True, comment="ETC 키워드 기준")
    direction = Column(String(50), comment="기준 방향 (Enum 문자열로 저장)")
    semester = Column(String(100), comment="기준 학기 (Enum 문자열로 저장)")
    description = Column(String(500), nullable=True, comment="원본 텍스트")

    required_qualifications = Column(TEXT, comment="장학금 지원을 위한 필수 자격 조건 목록 (JSON 문자열로 저장)")
    preference_qualifications = Column(TEXT, comment="우대 조건 목록 (JSON 문자열로 저장)")