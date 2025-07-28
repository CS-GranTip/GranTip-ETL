# db/models/region.py
from sqlalchemy import Column, BIGINT, Integer, String, ForeignKey, TIMESTAMP, text
from db.database import Base

class Region(Base):
    __tablename__ = "region"
    __table_args__ = {'extend_existing': True}  # 이 줄 추가!
    
    id = Column(BIGINT, primary_key=True, index=True, comment="고유 ID (PK)")
    parent_id = Column(BIGINT, ForeignKey("region.id"), nullable=True, comment="상위 지역 ID (FK, 자기 참조)")
    region_name = Column(String(255), nullable=False, comment="지역 이름")
    region_level = Column(Integer, nullable=False, comment="지역 계층 레벨")

    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))