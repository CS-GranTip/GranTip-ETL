from sqlalchemy import Column, Integer, String, ForeignKey
from ..database import Base  # 👈 DB 설정을 중앙에서 관리하기 위해 Base를 가져옵니다.

class Region(Base):
    __tablename__ = 'region'
    
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('region.id'), nullable=True)
    region_name = Column(String(255), nullable=False)
    region_level = Column(Integer, nullable=False)
