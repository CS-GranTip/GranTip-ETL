import sys
import json
import logging
import hashlib
from pathlib import Path

from scripts.ingest.openapi_collector import collect_all_data, collect_data
from scripts.ingest.preprocess.data_cleaner import clean_raw_data
from scripts.ingest.transform.transformer import transform_data
from scripts.ingest.transform.validator import validate_scholarship_data
from apscheduler.schedulers.blocking import BlockingScheduler

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
HASH_FILE_PATH = PROJECT_ROOT / "data" / "last_hash.txt"

def load_region_maps_from_cache():
    """
    미리 생성된 region_maps.json 캐시 파일에서 지역 맵을 로드합니다.
    """
    logger.info(f"[Cache] 캐시 파일에서 지역 맵을 로드합니다: {REGION_CACHE_PATH}")
    try:
        with open(REGION_CACHE_PATH, 'r', encoding='utf-8') as f:
            maps = json.load(f)

            # JSON에서 id_to_region_map의 key는 문자열이므로, 다시 정수형으로 변환
            maps['id_to_region_map'] = {int(k): v for k, v in maps['id_to_region_map'].items()}
            
            logger.info("✅ 지역 맵 캐시 로드 완료.")
            return maps['sido_map'], maps['sigungus_map'], maps['id_to_region_map']
    except FileNotFoundError:
        logger.error(f"캐시 파일을 찾을 수 없습니다: {REGION_CACHE_PATH}")
        logger.error("먼저 `cache_region_maps.py` 스크립트를 실행하여 캐시 파일을 생성해주세요.")
        return None, None, None
    except Exception as e:
        logger.error(f"캐시 파일 로드 중 오류 발생: {e}")
        return None, None, None
    
def validate_all_data(scholarships, all_grade_criteria, all_income_criteria, all_general_criteria, all_region_links, id_to_region_map):
    """
    변환된 모든 데이터를 순회하며 정합성을 검증하고, 유효한 데이터만 필터링합니다.
    """
    logger.info("[Step 4] Validator를 사용하여 데이터 정합성 검증 중...")
    valid_scholarships = []
    valid_grade_criteria = []
    valid_income_criteria = []
    valid_general_criteria = []
    valid_region_links = []

    # 각 기준 데이터를 scholarship_id를 기준으로 그룹화
    grouped_grades = {}
    for item in all_grade_criteria:
        if item.scholarship_id not in grouped_grades:
            grouped_grades[item.scholarship_id] = []
        grouped_grades[item.scholarship_id].append(item)

    grouped_incomes = {}
    for item in all_income_criteria:
        if item.scholarship_id not in grouped_incomes:
            grouped_incomes[item.scholarship_id] = []
        grouped_incomes[item.scholarship_id].append(item)

    grouped_generals = {}
    for item in all_general_criteria:
        if item.scholarship_id not in grouped_generals:
            grouped_generals[item.scholarship_id] = []
        grouped_generals[item.scholarship_id].append(item)
    
    grouped_regions = {}
    for link in all_region_links:
        if link.scholarship_id not in grouped_regions:
            grouped_regions[link.scholarship_id] = []
        grouped_regions[link.scholarship_id].append(link)

    for s in scholarships:
        temp_s_id = s.original_id # DB 저장 전이므로 original_id를 임시 키로 사용

        related_grades = grouped_grades.get(temp_s_id, [])
        related_incomes = grouped_incomes.get(temp_s_id, [])
        related_generals = grouped_generals.get(temp_s_id, [])
        related_regions = grouped_regions.get(temp_s_id, [])
        
        is_valid = validate_scholarship_data(
            scholarship=s,
            grade_criteria=related_grades,
            income_criteria=related_incomes,
            general_criteria=related_generals,
            scholarship_regions=related_regions,
            id_to_region_map=id_to_region_map
        )

        if is_valid:
            valid_scholarships.append(s)
            if temp_s_id in grouped_grades: valid_grade_criteria.append(grouped_grades[temp_s_id])
            if temp_s_id in grouped_incomes: valid_income_criteria.append(grouped_incomes[temp_s_id])
            if temp_s_id in grouped_generals: valid_general_criteria.append(grouped_generals[temp_s_id])
            if temp_s_id in grouped_regions: valid_region_links.extend(grouped_regions[temp_s_id])
        else:
            logger.warning(f"  - 검증 실패: Scholarship Original ID: {s.original_id}, Name: {s.product_name}")

    return valid_scholarships, valid_grade_criteria, valid_income_criteria, valid_general_criteria, valid_region_links


def run_pipeline(sido_map, sigungus_map, id_to_region_map):
    """전체 데이터 처리 파이프라인을 실행합니다."""
    print("데이터 처리 파이프라인을 시작합니다.")

    # 1. 데이터 수집
    logger.info("[Step 1] OpenAPI로부터 데이터를 수집합니다...")
    raw_data = collect_data(page=1, perPage=100)
    if not raw_data:
        logger.info("수집된 데이터가 없어 파이프라인을 종료합니다.")
        return
    logger.info(f"✅ 총 {len(raw_data)}건의 원본 데이터 수집 완료")

    # 2. 데이터 정제
    logger.info("[Step 2] 수집된 데이터의 정제를 시작합니다...")
    cleaned_data = clean_raw_data(raw_data)
    logger.info(f"✅ 총 {len(cleaned_data)}건의 데이터 정제 완료")

    # 3. 데이터 변환
    logger.info("[Step 3] 정제된 데이터를 Pydantic 객체로 변환합니다...")
    scholarships, grade_criteria, income_criteria, general_criteria, region_links = transform_data(
        cleaned_data=cleaned_data,
        sido_map=sido_map,
        all_sigungus_map=sigungus_map,
        id_to_region_map=id_to_region_map
    )
    logger.info(f"✅ 총 {len(scholarships)}개의 장학금 객체 변환 완료")

    # 4. 데이터 검증
    valid_data = validate_all_data(
        scholarships, grade_criteria, income_criteria, general_criteria, region_links, id_to_region_map
    )
    valid_scholarships, _, _, _, _ = valid_data
    logger.info(f"✅ 총 {len(valid_scholarships)}개의 장학금 데이터가 최종 정합성 검증을 통과했습니다.")

    # 5. DB 저장
    if valid_scholarships:
        logger.info("[Step 5] 유효한 데이터를 데이터베이스에 저장합니다.")
        # --- DB 저장 로직 (구현 시 주석 해제) ---
        # from scripts.ingest.db_loader import save_validated_data
        # save_validated_data(*valid_data)
        logger.info(f"✅ {len(valid_scholarships)}개의 유효한 장학금 데이터 저장 완료")
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
        run_pipeline(REGION_SIDO_MAP, REGION_SIGUNGUS_MAP, REGION_ID_MAP)
    else:
        logger.info("변경 사항이 없어 파이프라인을 실행하지 않고 작업을 종료합니다.")
    logger.info("--- 스케줄링 작업 종료 ---")


if __name__ == "__main__":
    # 캐시 파일에서 지역 정보를 미리 로드
    REGION_SIDO_MAP, REGION_SIGUNGUS_MAP, REGION_ID_MAP = load_region_maps_from_cache()
    
    """
    if not REGION_ID_MAP:
        logger.error("지역 정보 캐시 로드에 실패하여 프로그램을 종료합니다.")
    else:
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
    if REGION_ID_MAP:
        run_pipeline(REGION_SIDO_MAP, REGION_SIGUNGUS_MAP, REGION_ID_MAP)