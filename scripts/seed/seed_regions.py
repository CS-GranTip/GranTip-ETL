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


def seed_db():
    """regions.json 파일을 읽어 Region 테이블을 채웁니다."""
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

        regions_to_add = []
        id_counter = 1
        sido_map = {}  # 시/도 이름과 생성된 ID를 매핑

        # '전국' 기본 데이터 추가
        regions_to_add.append(Region(id=id_counter, parent_id=None, region_name='전국', region_level=0))
        id_counter += 1
        
        # 시/도 (Level 1) 데이터 생성
        for sido_name in region_data.keys():
            sido_id = id_counter
            sido_map[sido_name] = sido_id
            regions_to_add.append(
                Region(id=sido_id, parent_id=None, region_name=sido_name, region_level=1)
            )
            id_counter += 1

        # 시/군/구 (Level 2) 데이터 생성
        for sido_name, sigungu_list in region_data.items():
            parent_id = sido_map[sido_name]
            if not sigungu_list or (len(sigungu_list) == 1 and sigungu_list[0] == sido_name):
                continue
            
            for sigungu_name in sigungu_list:
                regions_to_add.append(
                    Region(id=id_counter, parent_id=parent_id, region_name=sigungu_name, region_level=2)
                )
                id_counter += 1
        
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