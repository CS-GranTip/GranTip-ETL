import json
import sys
from pathlib import Path
from typing import Dict

# --- 프로젝트 루트 경로 설정 ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from db.database import SessionLocal
from db.models.university_category import UniversityCategory as CategoryDBModel

# 생성될 캐시 파일 경로
CACHE_FILE_PATH = PROJECT_ROOT / "data" / "university_category_maps.json"

def get_category_maps_from_db() -> Dict[str, Dict]:
    """
    DB에서 대학 구분 카테고리 정보를 조회하여 맵을 생성합니다.
    name_to_id_map: {'이름': id}
    """
    print("데이터베이스에서 'university_category' 정보를 조회합니다...")
    db = SessionLocal()
    try:
        categories = db.query(CategoryDBModel).all()
        if not categories:
            raise Exception("DB에 카테고리 데이터가 없습니다. seed_university_categories.py를 먼저 실행하세요.")
        
        name_to_id_map = {}

        for category in categories:
            name_to_id_map[category.name] = category.id
            
        print(f"총 {len(name_to_id_map)}개의 카테고리 맵을 생성했습니다.")
        
        return name_to_id_map
    finally:
        db.close()

def create_cache_file():
    """DB에서 카테고리 맵을 가져와 JSON 파일로 저장합니다."""
    print("대학 구분 카테고리 맵 캐시 파일 생성을 시작합니다.")
    try:
        name_to_id_map = get_category_maps_from_db()
        
        # 캐시 파일이 저장될 디렉토리가 없으면 생성
        CACHE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        cache_data = {
            "name_to_id_map": name_to_id_map
        }
        
        with open(CACHE_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
            
        print(f"캐시 파일이 성공적으로 생성되었습니다: {CACHE_FILE_PATH}")

    except Exception as e:
        print(f"[오류] 캐시 파일 생성 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    create_cache_file()