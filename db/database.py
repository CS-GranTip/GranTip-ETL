from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# DB 연결, 세션, 모델이 공유할 Base를 중앙에서 관리

# MySQL + PyMySQL 드라이버 사용 기준
# mysql+pymysql://<사용자이름>:<비밀번호>@<호스트>:<포트>/<DB이름>?charset=utf8mb4
DATABASE_URL = "mysql+pymysql://root:1234@localhost:3307/grantip?charset=utf8mb4"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()