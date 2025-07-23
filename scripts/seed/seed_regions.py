import json
import sys
from pathlib import Path
from sqlalchemy import text

# 프로젝트 루트 경로를 시스템 경로에 추가하여 db 모듈을 찾을 수 있도록 함
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# 중앙에서 관리되는 모델과 DB 설정을 가져옴
from db.models.region import Region
from db.database import SessionLocal, engine, Base

# 경로 변수 정의
JSON_FILE_PATH = PROJECT_ROOT / "data" / "regions.json"
REGION_MAPS_PATH = PROJECT_ROOT / "data" / "region_maps.json"


def seed_db():
    """regions.json 및 region_maps.json 파일을 읽어 Region 테이블을 채웁니다."""
    db = SessionLocal()
    try:
        print("기존 데이터를 삭제합니다.")
        db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        db.execute(text("TRUNCATE TABLE region;"))
        db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.commit()

        print(f"{JSON_FILE_PATH} 파일을 읽습니다.")
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            region_data = json.load(f)

        print(f"{REGION_MAPS_PATH} 파일을 읽습니다.")
        with open(REGION_MAPS_PATH, 'r', encoding='utf-8') as f:
            region_maps = json.load(f)

        regions_to_add = []
        id_counter = 1
        sido_map = region_maps['sido_map']  # 시/도 이름과 ID 매핑
        sigungu_map = {}  # 시/군/구 이름과 ID, parent_id 매핑
        eupmyeondong_map = region_maps['eupmyeondong_map']  # 읍/면/동 이름과 ID, parent_id, sido, sigungu 매핑

        # '전국' 기본 데이터 추가 (Level 0)
        regions_to_add.append(Region(id=id_counter, parent_id=None, region_name='전국', region_level=0))
        id_counter += 1
        print(f"Level 0 (전국): 1개 데이터 추가 준비")

        # 시/도 (Level 1) 데이터 생성
        for sido_name, sido_id in sido_map.items():
            regions_to_add.append(
                Region(id=sido_id, parent_id=None, region_name=sido_name, region_level=1)
            )
            id_counter = max(id_counter, sido_id + 1)
        print(f"Level 1 (시/도): {len(sido_map)}개 데이터 추가 준비")

        # 시/군/구 (Level 2) 데이터 생성
        for sigungu_name, mappings in region_maps['sigungus_map'].items():
            for mapping in mappings:
                sigungu_id = mapping['id']
                parent_id = mapping['parent_id']
                regions_to_add.append(
                    Region(id=sigungu_id, parent_id=parent_id, region_name=sigungu_name, region_level=2)
                )
                if sigungu_name not in sigungu_map:
                    sigungu_map[sigungu_name] = []
                sigungu_map[sigungu_name].append({'id': sigungu_id, 'parent_id': parent_id})
                id_counter = max(id_counter, sigungu_id + 1)
        print(f"Level 2 (시/군/구): {sum(len(mappings) for mappings in region_maps['sigungus_map'].values())}개 데이터 추가 준비")

        # 읍/면/동 (Level 3) 데이터 생성
        eupmyeondong_count = 0
        processed_eupmyeondong = set()  # 중복 처리를 위한 집합

        # eupmyeondong_map을 사용하여 Level 3 데이터 추가
        for dong_name, mappings in eupmyeondong_map.items():
            for mapping in mappings:
                dong_id = mapping['id']
                parent_id = mapping['parent_id']
                sido_name = mapping['sido']
                sigungu_name = mapping['sigungu']
                
                # 동일한 ID가 이미 처리되었는지 확인
                if dong_id in processed_eupmyeondong:
                    continue
                
                # 유효한 parent_id인지 확인
                if sigungu_name in sigungu_map:
                    valid_parent = any(m['id'] == parent_id and m['parent_id'] == sido_map.get(sido_name) for m in sigungu_map[sigungu_name])
                    if not valid_parent:
                        print(f"경고: {sido_name} 아래 {sigungu_name}의 {dong_name}에 대한 parent_id {parent_id}가 유효하지 않습니다.")
                        continue
                else:
                    print(f"경고: {sigungu_name}이 sigungu_map에 없습니다. {dong_name} 건너뜁니다.")
                    continue
                
                regions_to_add.append(
                    Region(id=dong_id, parent_id=parent_id, region_name=dong_name, region_level=3)
                )
                processed_eupmyeondong.add(dong_id)
                eupmyeondong_count += 1
                id_counter = max(id_counter, dong_id + 1)

        # regions.json에서 추가적인 읍/면/동 데이터 확인
        for sido_name, sigungu_data in region_data.items():
            if sido_name not in sido_map:
                print(f"경고: {sido_name}이 sido_map에 없습니다. 건너뜁니다.")
                continue
            sido_id = sido_map[sido_name]
            for sigungu_name, dong_list in sigungu_data.items():
                if sigungu_name not in sigungu_map:
                    print(f"경고: {sido_name} 아래 {sigungu_name}이 sigungu_map에 없습니다. 건너뜁니다.")
                    continue
                parent_id = None
                for mapping in sigungu_map[sigungu_name]:
                    if mapping['parent_id'] == sido_id:
                        parent_id = mapping['id']
                        break
                if not parent_id:
                    print(f"경고: {sido_name} 아래 {sigungu_name}의 parent_id를 찾을 수 없습니다.")
                    continue
                for dong_name in dong_list:
                    # 이미 eupmyeondong_map에서 처리된 경우 건너뜀
                    if dong_name in eupmyeondong_map:
                        for mapping in eupmyeondong_map[dong_name]:
                            if mapping['sido'] == sido_name and mapping['sigungu'] == sigungu_name and mapping['id'] in processed_eupmyeondong:
                                continue
                    regions_to_add.append(
                        Region(id=id_counter, parent_id=parent_id, region_name=dong_name, region_level=3)
                    )
                    id_counter += 1
                    eupmyeondong_count += 1
        print(f"Level 3 (읍/면/동): {eupmyeondong_count}개 데이터 추가 준비")

        print(f"총 {len(regions_to_add)}개의 지역 데이터를 준비했습니다. DB에 저장합니다.")
        db.add_all(regions_to_add)
        db.commit()
        
        print(f"지역 데이터 저장이 완료되었습니다.")

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