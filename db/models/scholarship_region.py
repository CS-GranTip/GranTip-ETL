from sqlalchemy import Column, Integer, ForeignKey
from db.database import Base

class ScholarshipRegion(Base):
    __tablename__ = "scholarship_region"
    __table_args__ = {'extend_existing': True}  # 이 줄 추가!
    
    id = Column(Integer, primary_key=True, index=True)
    scholarship_id = Column(Integer, ForeignKey("scholarship.id"))
    region_id = Column(Integer, ForeignKey("region.id"))