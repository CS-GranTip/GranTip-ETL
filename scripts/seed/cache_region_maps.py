import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

# --- 프로젝트 루트 경로 설정 ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from db.database import SessionLocal
from db.models.region import Region as RegionDBModel

# 생성될 캐시 파일 경로
CACHE_FILE_PATH = PROJECT_ROOT / "data" / "region_maps.json"

def get_region_maps_from_db() -> Tuple[Dict[str, int], Dict[str, List[Dict[str, int]]], Dict[int, Any]]:
    """DB에서 지역 정보를 조회하여 3가지 종류의 맵을 생성합니다."""
    print("[DB] 데이터베이스에서 지역 정보를 조회합니다...")
    db = SessionLocal()
    try:
        regions = db.query(RegionDBModel).all()
        if not regions:
            raise Exception("DB에 지역 데이터가 없습니다. seed_regions.py를 먼저 실행하세요.")
        
        sido_map, all_sigungus_map, id_to_region_map = {}, {}, {}

        for region in regions:
            # id_to_region_map은 key가 int이므로 JSON 저장을 위해 str로 변환
            id_to_region_map[str(region.id)] = {'name': region.region_name, 'parent_id': region.parent_id}
            if region.region_level == 1:
                sido_map[region.region_name] = region.id
            elif region.region_level == 2:
                if region.region_name not in all_sigungus_map:
                    all_sigungus_map[region.region_name] = []
                all_sigungus_map[region.region_name].append({'id': region.id, 'parent_id': region.parent_id})
        
        print(f"✅ {len(sido_map)}개의 시/도, {len(all_sigungus_map)}개의 시/군/구 맵을 생성했습니다.")
        return sido_map, all_sigungus_map, id_to_region_map
    finally:
        db.close()

def create_cache_file():
    """DB에서 지역 맵을 가져와 JSON 파일로 저장합니다."""
    print("지역 맵 캐시 파일 생성을 시작합니다.")
    sido_map, sigungus_map, id_map = get_region_maps_from_db()
    
    combined_maps = {
        "sido_map": sido_map,
        "sigungus_map": sigungus_map,
        "id_to_region_map": id_map
    }
    
    # 캐시 파일이 저장될 디렉토리가 없으면 생성
    CACHE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(CACHE_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(combined_maps, f, ensure_ascii=False, indent=4)
        
    print(f"✅ 캐시 파일이 성공적으로 생성되었습니다: {CACHE_FILE_PATH}")

if __name__ == "__main__":
    create_cache_file()