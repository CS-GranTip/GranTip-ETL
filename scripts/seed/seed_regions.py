import json
import sys
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session

# 프로젝트 루트 경로를 시스템 경로에 추가하여 db 모듈을 찾을 수 있도록 함
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# 중앙에서 관리되는 모델과 DB 설정을 가져옴
from db.models.region import Region
from db.database import SessionLocal, engine, Base

# 경로 변수 정의
REGIONS_JSON_PATH = PROJECT_ROOT / "data" / "regions.json"
REGION_MAPS_JSON_PATH = PROJECT_ROOT / "data" / "region_maps.json"
DB_FILE_PATH = PROJECT_ROOT / "region.db"

def seed_db(db: Session):
    """regions.json과 region_maps.json 파일을 읽어 Region 테이블을 채웁니다."""

    print("Region 테이블 스키마를 확인 및 생성합니다...")
    Base.metadata.create_all(bind=engine)

    try:
        print("기존 데이터를 삭제합니다.")
        db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        db.execute(text("TRUNCATE TABLE region;"))
        db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.commit()

        print(f"{REGIONS_JSON_PATH} 파일을 읽습니다.")
        with open(REGIONS_JSON_PATH, 'r', encoding='utf-8') as f:
            region_data = json.load(f)

        print(f"{REGION_MAPS_JSON_PATH} 파일을 읽습니다.")
        with open(REGION_MAPS_JSON_PATH, 'r', encoding='utf-8') as f:
            region_maps_data = json.load(f)

        regions_to_add = []
        used_ids = set()  # 사용된 ID를 추적
        id_counter = 1
        sido_map = {}  # 시/도 이름과 생성된 ID를 매핑
        sigungu_map = {}  # 시/군/구 이름과 생성된 ID를 매핑

        # '전국' 기본 데이터 추가
        while id_counter in used_ids:
            id_counter += 1
        regions_to_add.append(Region(id=id_counter, parent_id=None, region_name='전국', region_level=0))
        used_ids.add(id_counter)
        id_counter += 1
        
        # 시/도 (Level 1) 데이터 생성
        for sido_name in region_data.keys():
            while id_counter in used_ids:
                id_counter += 1
            sido_id = id_counter
            sido_map[sido_name] = sido_id
            regions_to_add.append(
                Region(id=sido_id, parent_id=None, region_name=sido_name, region_level=1)
            )
            used_ids.add(sido_id)
            id_counter += 1

        # 시/군/구 (Level 2) 데이터 생성
        for sido_name, sigungu_dict in region_data.items():
            parent_id = sido_map[sido_name]
            for sigungu_name in sigungu_dict.keys():
                while id_counter in used_ids:
                    id_counter += 1
                sigungu_id = id_counter
                sigungu_map[(sido_name, sigungu_name)] = sigungu_id
                regions_to_add.append(
                    Region(id=sigungu_id, parent_id=parent_id, region_name=sigungu_name, region_level=2)
                )
                used_ids.add(sigungu_id)
                id_counter += 1

        # 읍면동 (Level 3) 데이터 생성
        for sido_name, sigungu_dict in region_data.items():
            for sigungu_name, eupmyeondong_list in sigungu_dict.items():
                parent_id = sigungu_map.get((sido_name, sigungu_name))
                if not parent_id:
                    print(f"Warning: No parent ID found for {sido_name} - {sigungu_name}")
                    continue
                # region_maps.json에서 시/군/구 ID 목록 가져오기
                sigungu_ids = [sigungu["id"] for sigungu in region_maps_data["sigungus_map"].get(sigungu_name, [])]
                for eupmyeondong_name in eupmyeondong_list:
                    # region_maps.json에서 매핑된 ID 확인
                    eupmyeondong_id = None
                    eupmyeondong_entries = region_maps_data["eupmyeondong_map"].get(eupmyeondong_name, [])
                    for entry in eupmyeondong_entries:
                        if entry["parent_id"] in sigungu_ids and entry["id"] not in used_ids:
                            eupmyeondong_id = entry["id"]
                            break
                    if eupmyeondong_id is None or eupmyeondong_id in used_ids:
                        while id_counter in used_ids:
                            id_counter += 1
                        eupmyeondong_id = id_counter
                        id_counter += 1
                    regions_to_add.append(
                        Region(id=eupmyeondong_id, parent_id=parent_id, region_name=eupmyeondong_name, region_level=3)
                    )
                    used_ids.add(eupmyeondong_id)

        print(f"총 {len(regions_to_add)}개의 지역 데이터를 준비했습니다. DB에 저장합니다.")
        db.add_all(regions_to_add)
        db.commit()
        
        print(f"지역 데이터 저장이 완료되었습니다. ({DB_FILE_PATH})")

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        db.rollback()
    finally:
        db.close()

# 스크립트 실행
if __name__ == "__main__":
    print("Region 테이블을 생성합니다.")
    Base.metadata.create_all(bind=engine)
    
    seed_db()