import json
import sys
from pathlib import Path
from sqlalchemy.orm import Session

# --- 프로젝트 루트 경로 설정 ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from db.database import SessionLocal, engine, Base
from db.models.university_category import UniversityCategory

# --- 경로 및 파일 정의 ---
CATEGORIES_JSON_PATH = PROJECT_ROOT / "data" / "university_categories.json"

def seed_categories(db: Session):
    """
    university_categories.json 파일을 읽어 DB의 university_category 테이블에
    데이터가 없는 경우에만 초기 데이터를 삽입합니다.
    """

    print("UniversityCategory 테이블 스키마를 확인 및 생성합니다...")
    Base.metadata.create_all(bind=engine)

    try:
        # DB에 이미 데이터가 있는지 확인
        if db.query(UniversityCategory).first():
            print("'university_category' 테이블에 이미 데이터가 존재합니다. Seeding을 건너뜁니다.")
            return

        # JSON 파일에서 키워드 목록 읽기
        print(f"'{CATEGORIES_JSON_PATH}' 파일에서 카테고리 목록을 읽습니다.")
        with open(CATEGORIES_JSON_PATH, 'r', encoding='utf-8') as f:
            category_names = json.load(f)

        # DB에 저장할 객체 생성
        categories_to_add = [UniversityCategory(name=name) for name in category_names]

        # DB에 데이터 삽입
        print(f"총 {len(categories_to_add)}개의 카테고리 데이터를 DB에 저장합니다.")
        db.add_all(categories_to_add)
        db.commit()

        print("카테고리 데이터 초기화가 성공적으로 완료되었습니다.")

    except FileNotFoundError:
        print(f"[오류] '{CATEGORIES_JSON_PATH}' 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"[오류] 데이터 초기화 중 오류가 발생했습니다: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("UniversityCategory 테이블을 생성합니다 (존재하지 않는 경우).")
    Base.metadata.create_all(bind=engine)
    
    seed_categories()