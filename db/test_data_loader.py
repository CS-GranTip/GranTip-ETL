# db/test_data_load.py
# 실제 OpenAPI 데이터를 수집, 변환, 검증 후 DB에 적재하는 테스트 스크립트

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))  # 프로젝트 루트 추가

from db.database import Base, engine, SessionLocal
from db.data_loader import load_to_db
from scripts.ingest.openapi_collector import collect_data  # OpenAPI 데이터 수집
from scripts.ingest.transform.transformer import transform_data  # 데이터 변환
from scripts.ingest.transform.validator import validate_scholarship_data  # 데이터 검증

# 지역 맵 로드 함수 (transformer.py에서 복사)
def get_region_maps_from_db():
    from db.models.region import Region as RegionDBModel
    db = SessionLocal()
    try:
        regions = db.query(RegionDBModel).all()
        if not regions:
            print("⚠️ DB에 지역 데이터가 없습니다. seed_regions.py를 먼저 실행하세요.")
            sys.exit(1)
        
        sido_map = {}
        all_sigungus_map = {}
        id_to_region_map = {}

        for region in regions:
            id_to_region_map[region.id] = {'name': region.region_name, 'parent_id': region.parent_id}
            if region.region_level == 0 or region.region_level == 1:
                sido_map[region.region_name] = region.id
            elif region.region_level == 2:
                if region.region_name not in all_sigungus_map:
                    all_sigungus_map[region.region_name] = []
                all_sigungus_map[region.region_name].append({'id': region.id, 'parent_id': region.parent_id})
        
        return sido_map, all_sigungus_map, id_to_region_map
    finally:
        db.close()

def load_real_data_to_db(page_start=1, page_end=1, per_page=10):
    """
    OpenAPI에서 실제 데이터를 페이지별로 수집한 후, 변환/검증하여 DB에 적재합니다.
    :param page_start: 시작 페이지 번호
    :param page_end: 종료 페이지 번호
    :param per_page: 페이지당 데이터 수
    """
    # 지역 맵 로드 (지역 파싱에 필요)
    sido_map, all_sigungus_map, id_to_region_map = get_region_maps_from_db()
    
    all_valid_data = {"scholarships": [], "grades": [], "incomes": [], "generals": [], "regions": []}
    
    for page in range(page_start, page_end + 1):
        print(f"\n[Page {page}] OpenAPI 데이터 수집 중...")
        raw_data = collect_data(page=page, perPage=per_page)
        
        if not raw_data:
            print(f"Page {page}에서 데이터를 가져오지 못했습니다. 스킵합니다.")
            continue
        
        # 데이터 정제 (clean_data 함수가 없으므로 raw_data 사용. 실제로는 정제 로직 추가 권장)
        cleaned_data = raw_data
        
        print(f"[Page {page}] 데이터 변환 중...")
        scholarships, grades, incomes, generals, regions = transform_data(
            cleaned_data=cleaned_data,
            sido_map=sido_map,
            all_sigungus_map=all_sigungus_map,
            id_to_region_map=id_to_region_map
        )
        
        # 검증 및 필터링
        valid_scholarships = []
        valid_grades = []
        valid_incomes = []
        valid_generals = []
        valid_regions = []
        
        for s in scholarships:
            s_id = s.original_id
            related_grades = [g for g in grades if g.scholarship_id == s_id]
            related_incomes = [i for i in incomes if i.scholarship_id == s_id]
            related_generals = [gen for gen in generals if gen.scholarship_id == s_id]
            related_regions = [r for r in regions if r.scholarship_id == s_id]
            
            if validate_scholarship_data(
                scholarship=s,
                grade_criteria=related_grades,
                income_criteria=related_incomes,
                general_criteria=related_generals,
                scholarship_regions=related_regions,
                id_to_region_map=id_to_region_map
            ):
                valid_scholarships.append(s)
                valid_grades.extend(related_grades)
                valid_incomes.extend(related_incomes)
                valid_generals.extend(related_generals)
                valid_regions.extend(related_regions)
        
        # 누적
        all_valid_data["scholarships"].extend(valid_scholarships)
        all_valid_data["grades"].extend(valid_grades)
        all_valid_data["incomes"].extend(valid_incomes)
        all_valid_data["generals"].extend(valid_generals)
        all_valid_data["regions"].extend(valid_regions)
        
        print(f"[Page {page}] 유효 데이터: {len(valid_scholarships)}개 장학금")
    
    # DB 적재
    if all_valid_data["scholarships"]:
        print("\n유효 데이터를 DB에 적재 중...")
        load_to_db(all_valid_data)
        print("DB 적재 완료.")
    else:
        print("적재할 유효 데이터가 없습니다.")

if __name__ == "__main__":
    # 테이블 초기화 (테스트용, 실제 운영 환경에서는 주의)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # 실제 데이터 적재 테스트 (1~3페이지, 페이지당 10개 데이터)
    load_real_data_to_db(page_start=1, page_end=3, per_page=10)
    
    # 적재된 데이터 확인
    db = SessionLocal()
    try:
        from db.models.scholarship import Scholarship as ScholarshipDBModel
        print("\n저장된 Scholarship 데이터:")
        scholarships = db.query(ScholarshipDBModel).all()
        if scholarships:
            for s in scholarships:
                print(f"ID: {s.id}, Original ID: {s.original_id}, Name: {s.product_name}")
        else:
            print("저장된 데이터가 없습니다.")
    finally:
        db.close()
    print("실제 데이터 적재 테스트 완료.")