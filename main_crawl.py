import sys
import json
import logging
import hashlib
from pathlib import Path

from scripts.ingest.openapi_collector import collect_data
from scripts.ingest.preprocess.data_cleaner import clean_raw_data
from scripts.ingest.transform.transformer import transform_data
from scripts.ingest.transform.validator import validate_scholarship_data

from db.data_loader import load_to_db
from db.database import engine, Base, SessionLocal
from db.models.region import Region
from db.models.university_category import UniversityCategory
from scripts.seed.seed_regions import seed_db as seed_regions_db
from scripts.seed.seed_university_categories import seed_categories as seed_categories_db
from scripts.cache.cache_region_maps import create_cache_file as create_region_cache
from scripts.cache.cache_university_categories import create_cache_file as create_category_cache

from scripts.ingest.crawler.seoul_crawl import crawl_seoul_scholarships_to_json
from scripts.ingest.crawler.suwon_crawl import crawl_suwon_scholarships_to_json
from scripts.ingest.crawler.nonsan_crawl import crawl_nonsan_scholarships_to_json
from scripts.ingest.crawler.dreamspon_crawl import crawl_dreamspon_scholarships_to_json
from db.data_loader import load_to_db
from scripts.cache.cache_region_maps import create_cache_file as create_region_cache
from scripts.cache.cache_university_categories import create_cache_file as create_category_cache
from db.database import engine, Base, SessionLocal
from db.models.region import Region
from db.models.university_category import UniversityCategory

import asyncio

# --- 프로젝트 루트 경로 설정 ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent
except NameError:
    PROJECT_ROOT = Path.cwd()
sys.path.append(str(PROJECT_ROOT))

# --- 로깅 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 상수 정의 ---
REGION_CACHE_PATH = PROJECT_ROOT / "data" / "region_maps.json"
CATEGORY_CACHE_PATH = PROJECT_ROOT / "data" / "university_category_maps.json"
HASH_FILE_PATH = PROJECT_ROOT / "data" / "last_hash.txt"



def load_region_maps_from_cache():
    logger.info(f"[Cache] 캐시 파일에서 지역 맵을 로드합니다: {REGION_CACHE_PATH}")
    try:
        with open(REGION_CACHE_PATH, 'r', encoding='utf-8') as f:
            maps = json.load(f)     
            logger.info("✅ 지역 맵 캐시 로드 완료.")
            return maps['sido_map'], maps['sigungus_map'], maps['eupmyeondong_map'], maps['id_to_region_map']
    except FileNotFoundError:
        logger.warning("Region 캐시 파일이 없어 재생성합니다...")
        create_region_cache()
        return load_region_maps_from_cache()
    except Exception as e:
        logger.error(f"캐시 파일 로드 중 오류 발생: {e}")
        return None, None, None, None
    
def load_category_map_from_cache():
    """
    미리 생성된 university_category_maps.json 캐시 파일에서 카테고리 맵을 로드합니다.
    """
    logger.info(f"[Cache] 캐시 파일에서 대학 구분 카테고리 맵을 로드합니다: {CATEGORY_CACHE_PATH}")
    try:
        with open(CATEGORY_CACHE_PATH, 'r', encoding='utf-8') as f:
            maps = json.load(f)
            logger.info("✅ 대학 구분 카테고리 맵 캐시 로드 완료.")
            return maps['name_to_id_map']
    except FileNotFoundError:
        logger.error(f"캐시 파일을 찾을 수 없습니다: {CATEGORY_CACHE_PATH}")
        logger.error("먼저 `cache_university_categories.py` 스크립트를 실행하여 캐시 파일을 생성해주세요.")
        return None
    except Exception as e:
        logger.error(f"카테고리 맵 캐시 파일 로드 중 오류 발생: {e}")
        return None
        
def validate_all_data(scholarships, all_grade_criteria, all_income_criteria, all_general_criteria, all_region_links, id_to_region_map):
    logger.info("[Step 4] Validator를 사용하여 데이터 정합성 검증 중...")
    valid_scholarships = []
    valid_grade_criteria = []
    valid_income_criteria = []
    valid_general_criteria = []
    valid_region_links = []

    grouped_grades = {}
    for item in all_grade_criteria:
        grouped_grades.setdefault(item.scholarship_id, []).append(item)

    grouped_incomes = {}
    for item in all_income_criteria:
        grouped_incomes.setdefault(item.scholarship_id, []).append(item)

    grouped_generals = {}
    for item in all_general_criteria:
        grouped_generals.setdefault(item.scholarship_id, []).append(item)

    grouped_regions = {}
    for link in all_region_links:
        grouped_regions.setdefault(link.scholarship_id, []).append(link)

    for s in scholarships:
        sid = s.original_id
        is_valid = validate_scholarship_data(
            scholarship=s,
            grade_criteria=grouped_grades.get(sid, []),
            income_criteria=grouped_incomes.get(sid, []),
            general_criteria=grouped_generals.get(sid, []),
            scholarship_regions=grouped_regions.get(sid, []),
            id_to_region_map=id_to_region_map
        )
        if is_valid:
            valid_scholarships.append(s)
            valid_grade_criteria.extend(grouped_grades.get(sid, []))
            valid_income_criteria.extend(grouped_incomes.get(sid, []))
            valid_general_criteria.extend(grouped_generals.get(sid, []))
            valid_region_links.extend(grouped_regions.get(sid, []))

    return valid_scholarships, valid_grade_criteria, valid_income_criteria, valid_general_criteria, valid_region_links

def initialize_dependencies():
    """
    ETL 파이프라인 실행에 필요한 모든 사전 준비 작업을 자동으로 수행합니다.
    - DB 테이블 스키마 생성
    - 초기 데이터 삽입 (seeding)
    - 맵 캐시 파일 생성
    """
    logger.info("--- ETL 환경 자동 설정 시작 ---")
    
    # 모든 DB 테이블 스키마 생성 (존재하지 않을 경우)
    logger.info("데이터베이스 테이블 스키마를 확인 및 생성합니다...")
    #Base.metadata.drop_all(engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Region 데이터 확인 및 생성
        if not db.query(Region).first():
            logger.warning("Region 테이블이 비어있습니다. 데이터 초기화 및 캐싱을 시작합니다...")
            seed_regions_db(db)
            create_region_cache()
        else:
            logger.info("Region 데이터가 이미 존재합니다.")
            # DB에 데이터는 있는데 캐시 파일만 없을 경우, 캐시만 재생성
            if not REGION_CACHE_PATH.exists():
                logger.warning("Region 캐시 파일이 없습니다. 캐시를 재생성합니다...")
                create_region_cache()

        # UniversityCategory 데이터 확인 및 생성
        if not db.query(UniversityCategory).first():
            logger.warning("UniversityCategory 테이블이 비어있습니다. 데이터 초기화 및 캐싱을 시작합니다...")
            seed_categories_db(db)
            create_category_cache()
        else:
            logger.info("UniversityCategory 데이터가 이미 존재합니다.")
            if not CATEGORY_CACHE_PATH.exists():
                logger.warning("UniversityCategory 캐시 파일이 없습니다. 캐시를 재생성합니다...")
                create_category_cache()
    finally:
        db.close()

    logger.info("--- ETL 환경 자동 설정 완료 ---")

def run_pipeline(category_id_map, sido_map, sigungus_map, eupmyeondongs_map, id_to_region_map):
    """전체 데이터 처리 파이프라인을 실행합니다."""
    print("데이터 처리 파이프라인을 시작합니다.")

    logger.info("[Step 1] 서울장학재단 웹사이트로부터 데이터를 크롤링합니다...")
    seoul_base_url = "https://www.hissf.or.kr/home/kor/M821806781/scholarship/business/index.do"
    seoul_list_url = "https://www.hissf.or.kr/home/kor/M821806781/scholarship/business/view.do"
    dream_base_url = "https://www.dreamspon.com"
    dream_list_url = "/scholarship/list.html?&sch_type=all&sch_key=대학생"
    nonsan_base_url = "https://nonsan.go.kr/kor/html/sub03/030101.html?skey=title&sval=%EC%9E%A5%ED%95%99%ED%9A%8C&page_size=10"
    suwon_base_url = "https://suwon4u.or.kr/?p=21&page=2&page=1"
    raw_data = []
    #raw_data.extend(crawl_seoul_scholarships_to_json(seoul_base_url, seoul_list_url))
    raw_data.extend(asyncio.run(crawl_dreamspon_scholarships_to_json(dream_base_url, dream_list_url)))
    #raw_data.extend(crawl_suwon_scholarships_to_json(suwon_base_url))
    #raw_data.extend(crawl_nonsan_scholarships_to_json(nonsan_base_url))

    if not raw_data:
        logger.warning("수집된 데이터가 없어 파이프라인을 종료합니다.")
        return
    logger.info(f"✅ 총 {len(raw_data)}건의 원본 데이터 수집 완료")

    logger.info("[Step 2] 수집된 데이터의 정제를 시작합니다...")
    cleaned_data = clean_raw_data(raw_data)
    logger.info(f"✅ 총 {len(cleaned_data)}건의 데이터 정제 완료")

    logger.info("[Step 3] 정제된 데이터를 Pydantic 객체로 변환합니다...")
    scholarships, grades, incomes, generals, regions = transform_data(
        cleaned_data=cleaned_data,
        category_id_map=category_id_map,
        sido_map=sido_map,
        all_sigungus_map=sigungus_map,
        all_eupmyeondongs_map=eupmyeondongs_map,
        id_to_region_map=id_to_region_map
    )
    logger.info(f"✅ 총 {len(scholarships)}개의 장학금 객체 변환 완료")

    v_scholarships, v_grades, v_incomes, v_generals, v_regions = validate_all_data(
        scholarships, grades, incomes, generals, regions, id_to_region_map
    )
    logger.info(f"✅ 총 {len(v_scholarships)}개의 유효한 장학금 데이터가 최종 정합성 검증을 통과했습니다.")

    if v_scholarships:
        logger.info("[Step 5] 유효한 데이터를 데이터베이스에 저장합니다.")
        load_to_db({
            "scholarships": v_scholarships,
            "grades": v_grades,
            "incomes": v_incomes,
            "generals": v_generals,
            "regions": v_regions
        })
        logger.info(f"✅ {len(v_scholarships)}개의 장학금 데이터 저장 완료")
    else:
        logger.info("저장할 유효한 데이터가 없습니다.")

    print("모든 파이프라인 작업이 종료되었습니다.")

def check_for_updates() -> bool:
    """
    Open API의 데이터가 변경되었는지 확인합니다.
    첫 페이지의 첫 번째 데이터를 해시하여 이전 값과 비교합니다.
    """
    logger.info("Open API 업데이트 확인 중...")

    # 변경 감지를 위해 최소 데이터(1페이지 1개)만 가져옴
    latest_data = collect_data(page=1, perPage=1)

    if not latest_data:
        logger.warning("API에서 데이터를 가져오지 못해 업데이트를 확인할 수 없습니다.")
        return False
    
    # 데이터의 내용을 기준으로 해시 생성
    current_hash = hashlib.sha256(
        json.dumps(latest_data[0], sort_keys=True).encode('utf-8')
    ).hexdigest()

    # 이전 해시 값 불러오기
    try:
        with open(HASH_FILE_PATH, 'r', encoding='utf-8') as f:
            previous_hash = f.read().strip()
    except FileNotFoundError:
        previous_hash = None
        logger.info("이전 해시 파일이 없어 새로 생성합니다.")

    # 해시 값 비교
    if current_hash != previous_hash:
        logger.info("새로운 데이터 업데이트가 감지되었습니다.")
        # 새로운 해시 값을 파일에 저장
        with open(HASH_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(current_hash)
        return True
    else:
        logger.info("데이터 변경 사항이 없습니다.")
        return False
    

def run_scheduled_job():
    """
    스케줄러에 의해 실행될 작업.
    업데이트 확인 후, 변경 사항이 있을 때만 파이프라인을 실행합니다.
    """
    logger.info("--- 스케줄링 작업 시작 ---")
    if check_for_updates():
        logger.info("전체 데이터 처리 파이프라인을 시작합니다.")
        run_pipeline(CATEGORY_ID_MAP, REGION_SIDO_MAP, REGION_SIGUNGUS_MAP, RESION_EUPMYEONDONG_MAP, REGION_ID_MAP)
    else:
        logger.info("변경 사항이 없어 파이프라인을 실행하지 않고 작업을 종료합니다.")
    logger.info("--- 스케줄링 작업 종료 ---")


if __name__ == "__main__":

    initialize_dependencies()

    # 캐시 파일에서 지역 정보를 미리 로드
    REGION_SIDO_MAP, REGION_SIGUNGUS_MAP, RESION_EUPMYEONDONG_MAP, REGION_ID_MAP = load_region_maps_from_cache()
    CATEGORY_ID_MAP = load_category_map_from_cache()

    if not REGION_ID_MAP and CATEGORY_ID_MAP:
        logger.error("지역 또는 대학 구분 카테고리 정보 캐시 로드에 실패하여 프로그램을 종료합니다.")

    """
    # 스케줄러 설정
    scheduler = BlockingScheduler(timezone='Asia/Seoul')
        
    # 매일 새벽 4시에 run_scheduled_job 함수 실행
    scheduler.add_job(run_scheduled_job, 'cron', hour=4, minute=0)
        
    logger.info("스케줄러가 설정되었습니다. 매일 새벽 4시에 업데이트를 확인합니다.")
        
    # 프로그램 시작 시 1회 즉시 실행
    run_scheduled_job()

    try:
        # 스케줄러 시작
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("스케줄러를 종료합니다.")
        scheduler.shutdown()
    """
    run_pipeline(CATEGORY_ID_MAP, REGION_SIDO_MAP, REGION_SIGUNGUS_MAP, RESION_EUPMYEONDONG_MAP, REGION_ID_MAP)
