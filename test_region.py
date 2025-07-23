import sys
import json
import logging
import re
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any, Set

# --- 프로젝트 경로 설정 ---
# 이 스크립트가 프로젝트 루트에 있다고 가정합니다.
# (e.g., /path/to/GranTip-ETL/test_transformer.py)
try:
    PROJECT_ROOT = Path(__file__).resolve().parent
except NameError:
    PROJECT_ROOT = Path.cwd()
sys.path.append(str(PROJECT_ROOT))

# --- 로깅 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 필요한 모델 및 유틸리티 임포트 ---
# 실제 프로젝트 구조에 맞게 경로를 확인해주세요.
# 아래는 예시이며, 실제 파일이 없으면 임시 클래스를 만들어야 합니다.
try:
    from models.scholarship import Scholarship
    from models.criterion.grade_criterion import GradeCriterion
    from models.criterion.income_criterion import IncomeCriterion
    from models.criterion.general_criterion import GeneralCriterion
    from models.scholarship_region import ScholarshipRegion
    from scripts.ingest.transform.validator import validate_scholarship_data
    from scripts.ingest.transform.grade_parser import extract_grade_criteria
    from scripts.ingest.transform.income_parser import extract_income_criteria
    from scripts.ingest.transform.address_parser import address_parser
except ImportError as e:
    print(f"필요한 모듈을 임포트할 수 없습니다: {e}")
    print("스크립트를 프로젝트 루트 디렉토리에서 실행하고, 필요한 파일들이 있는지 확인해주세요.")
    # 임시 모델 정의 (스크립트 단독 실행을 위해)
    from pydantic import BaseModel, Field
    class ScholarshipRegion(BaseModel):
        scholarship_id: int
        region_id: int
    # ... 다른 모델들도 필요 시 여기에 임시로 정의할 수 있습니다.
    sys.exit(1)


# --- main.py 및 transformer.py의 핵심 함수들 ---
# 제공해주신 코드를 그대로 사용합니다.

def parse_selection_personnel(text: Optional[str]) -> Tuple[Optional[int], Optional[Dict[str, int]]]:
    if not text:
        return None, None
    if '각' in text and '씩' in text:
        total_match = re.search(r'총\s*(\d+)\s*명', text)
        if total_match:
            return int(total_match.group(1)), None
    text = text.replace('00명', '').strip()
    categorized: Dict[str, int] = {}
    total = None
    total_match = re.search(r'총\s*(\d+)\s*명', text)
    if total_match:
        total = int(total_match.group(1))
        text = text.replace(total_match.group(0), '')
    def find_and_add_categories(sub_text: str):
        pattern = r'([\w\s·/]+?)\s*[:/]?\s*(\d+)\s*명'
        matches = re.findall(pattern, sub_text)
        for cat_text, num_str in matches:
            key = re.sub(r'총|포함|제외|내외|이내|선발|정도|각', '', cat_text).strip()
            if key and not key.isdigit() and '명' not in key:
                categorized[key] = int(num_str)
    paren_matches = re.findall(r'\(([^)]+)\)', text)
    for content in paren_matches:
        find_and_add_categories(content)
    text = re.sub(r'\([^)]+\)', '', text)
    find_and_add_categories(text)
    if total is None and categorized:
        total = sum(categorized.values())
    final_categorized = categorized if categorized else None
    return total, final_categorized

def check_duplicate_support_restriction(text: Optional[str]) -> bool:
    if not text:
        return False
    permission_patterns = [r'중복\s*(수혜|지원)[이가]?\s*가능', r'등록금\s*범위\s*내', r'차액만\s*지급']
    prohibition_patterns = [
        r'중복\s*(수혜|지원|선발|지급|신청)\s*불가', r'중복\s*(수혜|지원)\s*금지',
        r'이중\s*(수혜|지원)\s*금지', r'(수혜|지원|선발)자\s*제외', r'1세대\s*1명만',
        r'한\s*종류만\s*수혜', r'가능하나\s*[^.]*?(불가|없음|제한|안됨)'
    ]
    is_permission_found = any(re.search(pattern, text) for pattern in permission_patterns)
    is_prohibition_found = any(re.search(pattern, text) for pattern in prohibition_patterns)
    if is_prohibition_found:
        return True
    if is_permission_found:
        return False
    general_restriction_keywords = ['타 장학금', '타장학금', '다른 장학금', '기수혜자', '이중지원']
    if any(keyword in text for keyword in general_restriction_keywords):
        return True
    return False

def extract_region_links(
    scholarship_id: int,
    raw_text: Optional[str],
    sido_map: Dict[str, int],
    all_sigungus_map: Dict[str, List[Dict[str, int]]],
    all_eupmyeondongs_map: Dict[str, List[Dict[str, Any]]],
    id_to_region_map: Dict[str, Any]
) -> List[ScholarshipRegion]:
    """
    [최종 수정] 안정적인 이전 로직을 기반으로 읍/면/동 처리를 추가하고,
    문맥을 먼저 파악한 후 하위 지역부터 상위 지역 순으로 처리하여 정확도를 높입니다.
    """
    if not raw_text:
        return []

    parsed_region_names = set(address_parser(raw_text))
    if not parsed_region_names:
        return []

    links: List[ScholarshipRegion] = []
    found_ids: Set[int] = set()

    # 재귀적으로 부모 지역을 모두 추가하는 헬퍼 함수
    def add_with_parents(region_id: Optional[int]):
        if region_id is None or region_id in found_ids:
            return
        
        found_ids.add(region_id)
        links.append(ScholarshipRegion(scholarship_id=scholarship_id, region_id=region_id))
        
        region_info = id_to_region_map.get(str(region_id))
        if region_info:
            add_with_parents(region_info.get('parent_id'))

    # --- 1. 문맥 정보 수집 ---
    # 텍스트에 명시적으로 언급된 모든 시/도와 시/군/구를 먼저 파악
    sidos_in_text = {name: sido_map[name] for name in parsed_region_names if name in sido_map}
    sigungus_in_text = {name for name in parsed_region_names if name in all_sigungus_map}

    # --- 2. 가장 구체적인 단위부터 처리하여 상위 지역을 함께 추가 ---

    # 2-1. 읍/면/동 처리
    for name in parsed_region_names:
        if name in all_eupmyeondongs_map:
            possible_matches = all_eupmyeondongs_map[name]
            match_to_add = None
            if len(possible_matches) == 1:
                match_to_add = possible_matches[0]
            else: # 문맥(함께 언급된 시/도, 시/군/구)을 이용해 정확한 지역 특정
                for match in possible_matches:
                    if match.get('sido') in sidos_in_text and match.get('sigungu') in sigungus_in_text:
                        match_to_add = match
                        break
            if match_to_add:
                add_with_parents(match_to_add.get('id'))

    # 2-2. 시/군/구 처리
    for name in parsed_region_names:
        if name in all_sigungus_map:
            possible_matches = all_sigungus_map[name]
            match_to_add = None
            if len(possible_matches) == 1:
                match_to_add = possible_matches[0]
            else: # 문맥(함께 언급된 시/도)을 이용해 정확한 지역 특정
                for match in possible_matches:
                    if match.get('parent_id') in sidos_in_text.values():
                        match_to_add = match
                        break
            if match_to_add:
                add_with_parents(match_to_add.get('id'))

    # 2-3. 시/도 처리
    # 시/도만 단독으로 언급된 경우, 위에서 추가되지 않았으므로 여기서 추가
    for sido_id in sidos_in_text.values():
        add_with_parents(sido_id)

    # 최종적으로 중복 제거 후 반환 (안전장치)
    final_links = list({link.region_id: link for link in links}.values())
    return final_links

def transform_data(
        cleaned_data: List[Dict[str, Any]],
        sido_map: Dict[str, int],
        all_sigungus_map: Dict[str, List[Dict[str, int]]],
        all_eupmyeondongs_map: Dict[str, List[Dict[str, Any]]],
        id_to_region_map: Dict[str, Any]
) -> Tuple[List[Any], List[Any], List[Any], List[Any], List[ScholarshipRegion]]:
    scholarship_models = []
    grade_criteria_models = []
    income_criteria_models = []
    general_criteria_models = []
    scholarship_region_models = []
    for row in cleaned_data:
        try:
            scholarship_data = row.copy()
            temp_id = row.get("번호")
            if temp_id is None: continue
            
            # 다른 파서들은 이 테스트의 핵심이 아니므로 임시로 빈 리스트를 반환하도록 처리
            grade_criterias = [] # extract_grade_criteria(...)
            income_criterias = [] # extract_income_criteria(...)
            general_criterias = [] # extract_income_criteria(...)
            
            region_links = extract_region_links(
                scholarship_id=temp_id,
                raw_text=row.get("지역거주여부 상세내용"),
                sido_map=sido_map,
                all_sigungus_map=all_sigungus_map,
                all_eupmyeondongs_map=all_eupmyeondongs_map,
                id_to_region_map=id_to_region_map
            )
            # ... (다른 필드 처리 로직은 생략)
            scholarship_region_models.extend(region_links)
        except Exception as e:
            logger.error(f"알 수 없는 에러 발생 (ID: {row.get('번호', 'N/A')}): {e}")
    return [], [], [], [], scholarship_region_models


# --- 캐시 로드 함수 ---
REGION_CACHE_PATH = PROJECT_ROOT / "data" / "region_maps.json"

def load_region_maps_from_cache():
    logger.info(f"[Cache] 캐시 파일에서 지역 맵을 로드합니다: {REGION_CACHE_PATH}")
    try:
        with open(REGION_CACHE_PATH, 'r', encoding='utf-8') as f:
            maps = json.load(f)
        logger.info("✅ 지역 맵 캐시 로드 완료.")
        return maps['sido_map'], maps['sigungus_map'], maps['eupmyeondong_map'], maps['id_to_region_map']
    except FileNotFoundError:
        logger.error(f"캐시 파일을 찾을 수 없습니다: {REGION_CACHE_PATH}")
        return None, None, None, None
    except Exception as e:
        logger.error(f"캐시 파일 로드 중 오류 발생: {e}")
        return None, None, None, None

# --- 메인 실행 블록 ---
if __name__ == "__main__":
    # 1. 캐시 파일에서 지역 맵 로드
    sido_map, sigungus_map, eupmyeondongs_map, id_to_region_map = load_region_maps_from_cache()

    if not id_to_region_map:
        logger.error("지역 맵 로드 실패. 테스트를 종료합니다.")
    else:
        # 2. 테스트할 샘플 데이터 정의 (실제 데이터와 유사하게)
        sample_cleaned_data = [
            {'번호': 684, '지역거주여부 상세내용': '○ 선발 공고일 기준 1년전부터 계속해서 본인 또는 친권자가 고성군에 주민등록이 되어 있는 자'},
            {'번호': 805, '지역거주여부 상세내용': '○ 부모(보호자) 또는 본인이 옥천군에 주소를 두고 장학생 선발 공고일 현재 1년 이상 계속 거주'},
            {'번호': 945, '지역거주여부 상세내용': '○ 공고일 기준 송정동에 주소를 두고 1년 이상 거주한 대학생'},
            {'번호': 1013, '지역거주여부 상세내용': '○ 광주광역시 광산구 거주자'},
            {'번호': 9999, '지역거주여부 상세내용': '○ 2024년 11월 현재 해당동에 1년 이상 거주하는 자○ 해당동: 가양1동/가양2동/가양3동/방화3동/등촌3동'} # 읍/면/동 테스트용
        ]

        # 3. 데이터 변환 함수 실행
        logger.info("[Step] Transformer를 사용하여 Pydantic 객체로 변환 중...")
        _, _, _, _, all_region_links = transform_data(
            cleaned_data=sample_cleaned_data,
            sido_map=sido_map,
            all_sigungus_map=sigungus_map,
            all_eupmyeondongs_map=eupmyeondongs_map,
            id_to_region_map=id_to_region_map
        )

        # 4. 결과 출력
        logger.info("\n--- [결과] extract_region_links 함수가 생성한 ScholarshipRegion 객체 ---")
        
        if not all_region_links:
            print("\n>> 추출된 지역 정보가 없습니다. address_parser 또는 맵핑 데이터를 확인해보세요.")
        else:
            # scholarship_id 별로 그룹화하여 출력
            grouped_links = {}
            for link in all_region_links:
                if link.scholarship_id not in grouped_links:
                    grouped_links[link.scholarship_id] = []
                grouped_links[link.scholarship_id].append(link)

            for scholarship_id, links in sorted(grouped_links.items()):
                # 원본 텍스트 찾기
                original_text = next((item['지역거주여부 상세내용'] for item in sample_cleaned_data if item['번호'] == scholarship_id), "N/A")
                print(f"\n--- Scholarship ID: {scholarship_id} ---")
                print(f"  - Input Text: \"{original_text}\"")
                
                # ID 순으로 정렬하여 출력
                for link in sorted(links, key=lambda x: x.region_id):
                    region_info = id_to_region_map.get(str(link.region_id), {})
                    name = region_info.get('name', '알 수 없음')
                    parent_id = region_info.get('parent_id', '없음')
                    print(f"  - Extracted: region_id={link.region_id} (Name: {name}, Parent ID: {parent_id})")