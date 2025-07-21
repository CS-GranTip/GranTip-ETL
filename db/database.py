# db/database.py
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# DB 연결, 세션, 모델이 공유할 Base를 중앙에서 관리
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOTENV_PATH = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=DOTENV_PATH)

# DATABASE_URL 로드, 기본값으로 MySQL 설정
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://grantip_user:your_password@localhost/grantip_db")

if DATABASE_URL is None:
    raise ValueError("DATABASE_URL 환경 변수를 찾을 수 없습니다. .env 파일 또는 기본값 확인 필요.")

# SQLAlchemy 엔진 생성
engine = create_engine(DATABASE_URL)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스
Base = declarative_base()

def get_db():
    """세션 의존성 주입용 제너레이터"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
Base.metadata.clear()
