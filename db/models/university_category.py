from sqlalchemy import Column, BIGINT, String, Table, ForeignKey, TIMESTAMP, text
from sqlalchemy.orm import relationship
from db.database import Base

# 연결 테이블
scholarship_university_category_table = Table(
    'scholarship_university_category',  # DB에 생성될 테이블 이름
    Base.metadata,
    Column('scholarship_id', BIGINT, ForeignKey('scholarship.id'), primary_key=True),
    Column('university_category_id', BIGINT, ForeignKey('university_category.id'), primary_key=True)
)

class UniversityCategory(Base):
    __tablename__ = "university_category"
    __table_args__ = {'extend_existing': True}
    
    id = Column(BIGINT, primary_key=True, autoincrement=True)

    name = Column(String(255), nullable=False, unique=True, index=True)

    scholarships = relationship(
        "Scholarship",
        secondary="scholarship_university_category", # 중간 테이블 이름
        back_populates="university_categories"       # Scholarship 엔티티에 있는 필드 이름
    )

    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))