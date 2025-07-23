from typing import Tuple, Optional, List, Dict, Any, Set

from pydantic import ValidationError

from models.scholarship import Scholarship
from models.criterion.grade_criterion import GradeCriterion
from models.criterion.income_criterion import IncomeCriterion
from models.criterion.general_criterion import GeneralCriterion
from models.scholarship_region import ScholarshipRegion

from .validator import validate_scholarship_data
from .grade_parser import extract_grade_criteria
from .income_parser import extract_income_criteria
from .address_parser import address_parser
import re
import sys
from pathlib import Path

def parse_selection_personnel(text: Optional[str]) -> Tuple[Optional[int], Optional[Dict[str, int]]]:
    """
    선발인원 상세내용을 파싱합니다.
    """
    if not text:
        return None, None
    
    if '각' in text and '씩' in text: # ex: 각 2명씩
        total_match = re.search(r'총\s*(\d+)\s*명', text)
        if total_match:
            # '총 O명'이 명시된 경우, 카테고리 파싱을 생략하고 total만 반환하여 불일치 검증을 피함
            return int(total_match.group(1)), None

    # 전처리: '00명' 제거 및 공백 정리
    text = text.replace('00명', '').strip()
    categorized: Dict[str, int] = {}
    total = None

    # 1. 명시적인 '총 O명'을 찾아 total로 확정하고, 텍스트에서 해당 부분 제거
    total_match = re.search(r'총\s*(\d+)\s*명', text)
    if total_match:
        total = int(total_match.group(1))
        text = text.replace(total_match.group(0), '')

    # 내부 함수: 주어진 텍스트에서 '카테고리 O명' 패턴을 찾아 categorized에 추가
    def find_and_add_categories(sub_text: str):
        # 'A 10명', 'B: 20명', 'C/30명' 등 다양한 구분자 처리
        pattern = r'([\w\s·/]+?)\s*[:/]?\s*(\d+)\s*명'
        matches = re.findall(pattern, sub_text)
        for cat_text, num_str in matches:
            # 불필요한 키워드와 공백 제거
            key = re.sub(r'총|포함|제외|내외|이내|선발|정도|각', '', cat_text).strip()
            if key and not key.isdigit() and '명' not in key:
                categorized[key] = int(num_str)

    # 2. 괄호 안의 내용을 먼저 파싱하고, 텍스트에서 제거
    paren_matches = re.findall(r'\(([^)]+)\)', text)
    for content in paren_matches:
        find_and_add_categories(content)
    text = re.sub(r'\([^)]+\)', '', text) # 괄호와 내용 모두 제거

    # 3. 괄호가 제거된 나머지 텍스트를 파싱
    find_and_add_categories(text)
    
    # 4. 명시적 '총'이 없었고, 카테고리가 존재하면 합계를 total로 추론
    if total is None and categorized:
        total = sum(categorized.values())

    final_categorized = categorized if categorized else None
    
    return total, final_categorized

def check_duplicate_support_restriction(text: Optional[str]) -> bool:
    """
    긍정/부정 패턴을 모두 탐색하고 가중치를 부여하여 최종 판단.
    '금지' 패턴이 하나라도 존재하면 '제한(True)'으로 판단하는 것을 우선한다.
    """
    if not text:
        return False

    # 허용을 의미하는 패턴 목록
    permission_patterns = [
        r'중복\s*(수혜|지원)[이가]?\s*가능',
        r'등록금\s*범위\s*내',
        r'차액만\s*지급',
    ]

    # 금지를 의미하는 패턴 목록
    prohibition_patterns = [
        r'중복\s*(수혜|지원|선발|지급|신청)\s*불가',
        r'중복\s*(수혜|지원)\s*금지',
        r'이중\s*(수혜|지원)\s*금지',
        r'(수혜|지원|선발)자\s*제외',
        r'1세대\s*1명만',
        r'한\s*종류만\s*수혜',
        # '가능'이 포함되지만 실제로는 금지인 경우
        r'가능하나\s*[^.]*?(불가|없음|제한|안됨)',
    ]

    # 텍스트에서 각 패턴의 발견 여부 확인
    is_permission_found = any(re.search(pattern, text) for pattern in permission_patterns)
    is_prohibition_found = any(re.search(pattern, text) for pattern in prohibition_patterns)

    # --- 최종 판단 로직 ---
    # 1. 금지 패턴이 하나라도 발견되면, 일부 허용 조항이 있더라도 '제한'으로 간주 (True)
    if is_prohibition_found:
        return True

    # 2. 금지 패턴은 없지만, 명백한 허용 패턴이 발견되면 '허용' (False)
    if is_permission_found:
        return False

    # 3. 명확한 허용/금지 패턴은 없지만, 일반적인 제한 키워드가 있다면 '제한'으로 간주 (True)
    general_restriction_keywords = [
        '타 장학금', '타장학금', '다른 장학금', '기수혜자', '이중지원'
    ]
    if any(keyword in text for keyword in general_restriction_keywords):
        return True

    # 4. 위의 모든 경우에 해당하지 않으면 제한 없음 (False)
    return False

def extract_region_links(
    scholarship_id: int,
    raw_text: Optional[str],
    org_text: Optional[str],
    sido_map: Dict[str, int],
    all_sigungus_map: Dict[str, List[Dict[str, int]]],
    all_eupmyeondongs_map: Dict[str, List[Dict[str, Any]]],
    id_to_region_map: Dict[str, Any]
) -> List[ScholarshipRegion]:
    """
    재귀(Recursion) 방식을 사용하여, 발견된 지역의 모든 상위 부모 지역을
    더욱 안정적으로 함께 추가하도록 개선합니다.
    """
    if not raw_text:
        return []

    parsed_region_names = address_parser(text=raw_text, org_name=org_text)
    if not parsed_region_names:
        return []

    links: List[ScholarshipRegion] = []
    found_ids: Set[int] = set()

    # --- 재귀 방식으로 부모 지역을 모두 추가하는 헬퍼 함수 ---
    def add_with_parents_recursive(region_id: Optional[int]):
        # region_id가 없거나, 이미 추가된 ID라면 재귀를 종료
        if region_id is None or region_id in found_ids:
            return

        # 현재 ID를 추가
        found_ids.add(region_id)
        links.append(ScholarshipRegion(scholarship_id=scholarship_id, region_id=region_id))

        # 현재 지역의 정보에서 부모 ID를 찾아, 부모에 대해 재귀 호출
        region_info = id_to_region_map.get(str(region_id))
        if region_info:
            add_with_parents_recursive(region_info.get('parent_id'))

    # 텍스트에 언급된 시/도, 시/군/구 이름을 미리 저장하여 문맥으로 활용
    sidos_in_text = {name for name in parsed_region_names if name in sido_map}
    sigungus_in_text = {name for name in parsed_region_names if name in all_sigungus_map}

    # --- 1. 읍/면/동 (가장 구체적인 단위) 먼저 처리 ---
    for name in parsed_region_names:
        if name in all_eupmyeondongs_map:
            possible_matches = all_eupmyeondongs_map[name]
            match_to_add = None
            
            if len(possible_matches) == 1:
                match_to_add = possible_matches[0]
            else:
                for match in possible_matches:
                    sido = match.get('sido')
                    sigungu = match.get('sigungu')
                    if sido and sigungu and sido in sidos_in_text and sigungu in sigungus_in_text:
                        match_to_add = match
                        break
            
            if match_to_add:
                add_with_parents_recursive(match_to_add.get('id'))

    # --- 2. 시/군/구 처리 ---
    for name in parsed_region_names:
        if name in all_sigungus_map:
            possible_matches = all_sigungus_map[name]
            match_to_add = None

            if len(possible_matches) == 1:
                match_to_add = possible_matches[0]
            else:
                sido_ids_in_text = {sido_map[sido_name] for sido_name in sidos_in_text}
                for match in possible_matches:
                    if match.get('parent_id') in sido_ids_in_text:
                        match_to_add = match
                        break
            
            if match_to_add:
                add_with_parents_recursive(match_to_add.get('id'))

    # --- 3. 시/도 처리 ---
    for name in parsed_region_names:
        if name in sido_map:
            add_with_parents_recursive(sido_map[name])

    return links


def transform_data(
        cleaned_data: List[Dict[str, Any]],
        sido_map: Dict[str, int],
        all_sigungus_map: Dict[str, List[Dict[str, int]]],
        all_eupmyeondongs_map: Dict[str, List[Dict[str, Any]]],
        id_to_region_map: Dict[int, Any]
) -> Tuple[List[Scholarship], List[GradeCriterion], List[IncomeCriterion], List[GeneralCriterion], List[ScholarshipRegion]]:
    """
    정제된 딕셔너리 리스트를 최종 Scholarship Pydantic 모델 리스트로 변환합니다.
    """
    scholarship_models = []
    grade_criteria_models = []
    income_criteria_models = []
    general_criteria_models = []
    scholarship_region_models = []

    for row in cleaned_data:
        try:
            scholarship_data = row.copy()
            # 원본 '번호'를 임시 ID로 사용
            """
            DB 저장 시에는 
            1. Scholarship 먼저 저장
            2. 생성된 실제 id 반환
            3. Scholarship의 original_id와 관련된 객체들의 FK를 실제 id로 교체 후 INSERT
            """
            temp_id = row.get("번호")
            if temp_id is None:
                continue # 임시 ID가 없으면 처리 불가
            
            # 각 기준별 Parser 호출하여 구조화된 객체 생성
            grade_criterias = extract_grade_criteria(
                scholarship_id=temp_id,
                raw_text=row.get("성적기준 상세내용")
            )

            parsed_income_data = extract_income_criteria(
                scholarship_id=temp_id,
                raw_text=row.get("소득기준 상세내용")
            )
            # 딕셔너리에서 각 리스트를 추출
            general_criterias = parsed_income_data.get("general_criteria", [])
            income_criterias = parsed_income_data.get("income_criteria", [])
            
            region_links = extract_region_links(
                scholarship_id=temp_id,
                raw_text=row.get("지역거주여부 상세내용"),
                org_text=row.get("운영기관명"),
                sido_map=sido_map,
                all_sigungus_map=all_sigungus_map,
                all_eupmyeondongs_map=all_eupmyeondongs_map,
                id_to_region_map=id_to_region_map
            )

            # 선발 인원 처리
            total_recipients, recipients_by_cat = parse_selection_personnel(row.get("선발인원 상세내용"))

            # 선발 인원 파싱 결과 scholarship_data 딕셔너리에 업데이트
            scholarship_data['num_of_recipients_total'] = total_recipients
            scholarship_data['recipients_by_category'] = recipients_by_cat

            # 추천 필요 여부 처리
            scholarship_data['is_recommendation_required'] = (
                row.get("추천필요여부 상세내용") is not None
            )

            # 중복 수혜 제한 여부 처리
            qualification_text = row.get("자격제한 상세내용", "")
            scholarship_data['is_duplicate_support_restricted'] = check_duplicate_support_restriction(qualification_text)

            # --- 가공된 분류 목록 매핑 ---
            # data_cleaner에서 처리된 리스트를 모델 필드명에 맞게 매핑
            scholarship_data['university_category'] = row.get('대학구분', [])
            scholarship_data['grade_category'] = row.get('학년구분', [])
            scholarship_data['department_category'] = row.get('학과구분', [])

            # Scholarship 모델 객체 생성 및 리스트에 추가
            scholarship_model = Scholarship.model_validate(scholarship_data)
            scholarship_models.append(scholarship_model)

            # 1:N 관계 객체들 각 리스트에 추가
            grade_criteria_models.extend(grade_criterias)
            income_criteria_models.extend(income_criterias)
            general_criteria_models.extend(general_criterias)
            scholarship_region_models.extend(region_links)

        except ValidationError as e:
            print(f"데이터 검증 실패 (ID: {row.get('번호', 'N/A')}): {e}")
        except Exception as e:
            print(f"알 수 없는 에러 발생 (ID: {row.get('번호', 'N/A')}): {e}")

    return scholarship_models, grade_criteria_models, income_criteria_models, general_criteria_models, scholarship_region_models



    

if __name__ == "__main__":
    # DB 모듈을 찾기 위해 프로젝트 루트 경로 추가
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    sys.path.append(str(PROJECT_ROOT))

    from db.database import SessionLocal
    from db.models.region import Region as RegionDBModel

    def get_region_maps_from_db() -> Tuple[Dict[str, int], Dict[str, List[Dict[str, int]]], Dict[int, Any]]:
        """
        DB에서 지역 정보를 조회하여 3가지 종류의 맵을 생성합니다.
        1. sido_map: {'서울특별시': 2, ...}
        2. all_sigungus_map: {'남구': [{'id': 47, 'parent_id': 3}, {'id': 61, 'parent_id': 4}, ...]}
        3. id_to_region_map: {2: {'name': '서울특별시', 'parent_id': None}, 47: {'name': '남구', 'parent_id': 3}, ...}
        """
        print("\n[DB] 데이터베이스에서 지역 정보를 조회하여 맵을 생성합니다...")
        db = SessionLocal()
        try:
            regions = db.query(RegionDBModel).all()
            if not regions:
                print("⚠️  경고: DB에 지역 데이터가 없습니다. 빈 맵을 반환합니다.")
                return {}, {}, {}
            
            sido_map: Dict[str, int] = {}
            all_sigungus_map: Dict[str, List[Dict[str, int]]] = {}
            id_to_region_map: Dict[int, Any] = {}

            for region in regions:
                id_to_region_map[region.id] = {'name': region.region_name, 'parent_id': region.parent_id}
                if region.region_level == 0 or region.region_level == 1: # 전국, 시/도
                    sido_map[region.region_name] = region.id
                elif region.region_level == 2: # 시/군/구
                    if region.region_name not in all_sigungus_map:
                        all_sigungus_map[region.region_name] = []
                    all_sigungus_map[region.region_name].append({'id': region.id, 'parent_id': region.parent_id})
            
            print(f"✅ {len(sido_map)}개의 시/도, {len(all_sigungus_map)}개의 시/군/구 맵을 생성했습니다.")
            return sido_map, all_sigungus_map, id_to_region_map
        finally:
            db.close()


    # --- 테스트 환경 설정 ---
    print("데이터 변환 및 검증 파이프라인 테스트 시작")

    # 1. 테스트용 샘플 데이터 (cleaner를 거친 상태라고 가정)
    sample_cleaned_data = [
        {'번호': 1, '상품명': '행복나눔 장학생', '운영기관명': '광주남구 장학회', '운영기관구분': '지자체(출자출연기관)', '상품구분': '장학금', '학자금유형구분': '지역연고', '모집시작일': '2024-09-23', '모집종료일': '2024-10-11', '홈페이지 주소': 'https://namgu.gwangju.kr', 
         '대학구분': ['4년제(5~6년제포함)'], '학년구분': ['대학2학기', '대학3학기', '대학4학기', '대학5학기', '대학6학기', '대학7학기', '대학8학기이상', '대학신입생'], '학과구분': ['공학계열', '교육계열', '사회계열', '예체능계열', '의약계열', '인문계열', '자연계열', '제한없음'], 
         '성적기준 상세내용': '○ 직전학기 12학점 이상 취득하고 성적 평균 2.75 이상인 자 (4.3만점은 2.6이상)', '소득기준 상세내용': '○ 2024년도 기준 중위소득 100% 이하인 가구', '지원내역 상세내용': '○ 1인당 100만원', 
         '특정자격 상세내용': '○ 공고일 현재 신청 학생 또는 학생의 부모가 광주광역시 남구에 주민등록상 1년 이상 주소를 두고 이고 유형별 자격과 요건을 충족하는 자', '지역거주여부 상세내용': '○ 보호자 또는 본인이 선발 공고일 현재 주민등록상 주소지가 광주광역시 남구로 1년 이상 두고 신청 요건을 갖춘 자', 
         '선발방법 상세내용': '○ 서류심사 (사무국) : 제출서류 신청요건 충족 및 직전학기 성적 등 확인○ 심사의결 (장학생 선발 심사위원회)○ 최종선정자 발표○ 선발결과 : 개별 안내 및 홈페이지 게시', '선발인원 상세내용': '○ 12명', '자격제한 상세내용': '○ 기술대학○ 2년 미만 교육과정의 각종 학교○ 평생교육법에 의거 설립한 학교○ 최근 2년 남구장학회 장학생으로 선발된 자○ 휴학(등록휴학 포함) / 제적 / 자퇴 / 졸업 등 학기 미등록자', 
         '추천필요여부 상세내용': None, '제출서류 상세내용': '○ 장학생 신청서○ 주민등록표등본○ 학생 명의의 가족관계증명서○ 건강보험 자격확인서○ 건강보험료 납부확인서○ 2024년 1학기 성적증명서○ 재학증명서○ 2학기 등록금 납입증명서○ 개인정보 수집·이용·제공 및 조회 동의서○ 통장 사본○ 가정환경 세대구성 관련증명서 (해당자)', 
         '성적기준 비고': None, '소득기준 비고': '직계가족의 3개월 평균국민건강보험료 산정', '지원내역 비고': '생활비 지원', '특정자격 비고': None, '지역거주여부 비고': None, '선발방법 비고': None, '선발인원 비고': None, '자격제한 비고': '자세한 사항 공고 참조', '추천필요여부 비고': None, '제출서류 비고': '자세한 사항 공고문 참조'},
        {'번호': 2, '상품명': '일반장학생', '운영기관명': '광주남구장학회', '운영기관구분': '지자체(출자출연기관)', '상품구분': '장학금', '학자금유형구분': '지역연고', '모집시작일': '2024-09-23', '모집종료일': '2024-10-11', '홈페이지 주소': 'https://namgu.gwangju.kr/', 
         '대학구분': [], '학년구분': [], '학과구분': [], '성적기준 상세내용': '○ 직전학기 12학점 이상 취득하고 성적 평균 3.0 이상인 자 (4.3만점은 2.8이상)', '소득 기준 상세내용': '○ 2024년도 기준 중위소득 150% 이하인 가구', '지원내역 상세내용': '○ 1인당 100만원', '특정자격 상세내용': '○ 공고일 현재 신청 학생 또는 학생의 부모가 광주광역시 남구에 주민등록상 1년 이상 주소를 두고 이 고 유형별 자격과 요건을 충족하는 자○ 24년 2학기 등록금 납부액이 100만원 이상인 자', 
         '지역거주여부 상세내용': '○ 공고일 현재 신청 학생 또는 학생의 부모가 광주광역시 남구에 주민등록상 1년 이상 주소를 두고 있는 자', '선발방법 상세내용': '○ 서류심사 (사무국) : 제출서류 신청요건 충족 및 직전학기 성적 등 확인○ 심사의결 (장학생 선발 심사위원회)○ 최종선정자 발표○ 선발결과 : 개별 안내 및 홈페이지 게시', '선발인원 상세내용': '○ 23명', '자격제한 상세내용': '○ 기술대학○ 2년 미만 교육과정의 각종 학교○ 평생교육법에 의거 설립한 학교○ 최근 2년 남구장 학회 장학생으로 선발된 자○ 휴학(등록휴학 포함) / 제적 / 자퇴 / 졸업 등 학기 미등록자', 
         '추천필요여부 상세내용': None, '제출서류 상세내용': '○ 장학생 신청서○ 주민등록표등본○ 학생 명의의 가족관계증명서○ 건강보험 자격확인서○ 건강보험료 납부확인서○ 2024년 1학기 성적증명서○ 재학증명서○ 2학기 등록금 납입증명서○ 개인정보 수집·이용·제공 및 조회 동의서○ 통장 사본○ 가정환경 세대구성 관련증명서 (해당자)', 
         '성적기준 비고': None, '소득기준 비고': '직계가족의 3개월 평균 국민건강보험료 산정', '지원내역 비고': '등록금 지원', '특정자격 비고': None, '지역거주여부 비고': None, '선발방법 비고': None, '선발인원 비고': None, '자격제한 비고': '자세한 사항 공고 참조', '추천필요여부 비고': None, '제출서류 비고': '자세한 사항 공고문 및 홈페이지 참조'},
        {'번호': 3, '상품명': '특별장학생', '운영기관명': '광주남구장학회', '운영기관구분': '지자체(출자출연기관)', '상품구분': '장학금', '학자금유형구분': '지역연고', '모집시작일': '2024-09-23', '모집종료일': '2024-10-11', '홈페이지 주소': 'https://namgu.gwangju.kr/', 
         '대학구분': ['4년제(5~6년제포함)'], '학년구분': ['대학2학기', '대학3학기', '대학4학기', '대학5학기', '대학6학기', '대학7학기', '대학8학기이상'], '학과구분': ['공학계열', '교육계열', '사회계열', '예체능계열', '의약계열', '인문계열', '자연계열', '제한없음'], 
         '성적기준 상세내용': '○ 직전학기 12학점 이상 취득하고 성적 평균 2.75 이상인 자 (4.3만점은 2.6이상)', '소득기준 상세내용': '○ 2024년도 기준 중위소득 150% 이하인 가구(직계가족의 3개월 평균국민건 강보험료 산정)', '지원내역 상세내용': '○ 1인 당 100만원○ 생활비 지원', '특정자격 상세내용': '○ 공고일 현재 신청 학생 또는 학생의 부모가 광주광역시 남구에 주민등록상 1년 이상 주소를 두고 이고 유형별 자격과 요건을 충족하는 자○ 3자녀 이상 가구 / 다문화 가구 / 본인 또는 가구원이 장애인인 가구 중 해 당자', '지역거주여부 상세내용': '○ 보호자 또는 본인이 선발 공고일 현재 주민등록상 주소지가 광주광역시 남구로 1년 이상 두고 신청 요건을 갖춘 자', 
         '선발방법 상세내용': '○ 서 류심사 (사무국) : 제출서류 신청요건 충족 및 직전학기 성적 등 확인○ 심사의결 (장학생 선발 심사위 원회)○ 최종선정자 발표○ 선발결과 : 개별 안내 및 홈페이지 게시', '선발인원 상세내용': '○ 11명', '자격제한 상세내용': '○ 기술대학○ 2년 미만 교육과정의 각족 학교○ 평생교육법에 의거 설립한 학교○ 최근 2 년 남구장학회 장학생으로 선발된 자○ 휴학(등록휴학 포함) / 제적 / 자퇴 / 졸업 등 학기 미등록자', 
         '추천필요여부 상세내용': None, '제출서류 상세내용': '○ 장학생 신청서○ 주민등록표등본○ 학생 명의의 가족관계증명서○ 건강보험 자격확인서○ 건강보험료 납부확인서○ 2024년 1학기 성적증명서○ 재학증명서○ 개인정보 수집·이용·제공 및 조회 동의서○ 통장 사본○ 가정환경 세대구성 관련증명서 (해당자)', 
         '성적기준 비고': None, '소득기준 비고': None, '지원내역 비고': None, '특정자격 비고': None, '지역거주여부 비고': None, '선발방법 비고': None, '선발인원 비고': None, '자격제한 비고': '자세한 사항은 첨부파일 참조', '추천필요여부 비고': None, '제출서류 비고': '자세한 사항은 첨부파일 참조'},
        {'번호': 4, '상품명': '장학금', '운영기관명': '농파장학회', '운영기관구분': '기타', '상품구분': '장학금', '학자금유형구분': '지역연고', '모집시작일': '2025-02-05', '모집종료일': '2025-02-10', '홈페이지 주소': 'http://cafe.daum.net/nongpa', 
         '대학구분': ['4년제(5~6년제포함)'], '학년구분': ['대학신입생'], '학과구분': ['공학계열', '교육계열', '사회계열', '예체능계열', '의약계열', '인문계열', '자연계열', '제한없음'], 
         '성적기준 상세내용': '○ 학업성적이 우수한 자', '소득기준 상세내용': '○ 가정형편이 곤란한 자', '지원내역 상세내용': None, '특정자격 상세내용': '○ 4년제 국내 국·공립 대학 합격자', '지역거주여부 상세내용': '○ 본적이 경남 출신인 자', '선발방법 상세내용': '○ 본 재단 선발위원회(이사회)에서 선발', 
         '선발인원 상세내용': '○ 약간 명', '자격제한 상세내용': '○ 형제 중 본 장학회에 입회된 자 또는 타 장학회 수혜자○ 한 세대 한 사람만 수혜원칙', '추천필요여부 상세내용': '○ 출신 고등학교장의 추천', '제출서류 상세내용': '○ 출신고등학교장의 추천서○ 자기 소개서○ 서약서○ 가족관계등록부1통 (학생본인의 본적이 나와있는)○ 수능성적표 첨 (사본가능)○ (추천서 포함)사진 2매(3cm× 4cm)○ 신입생 입학금 및 등록금 납입고지서 영수증사본 1부', 
         '성적기준 비고': None, '소득기준 비고': None, '지원내역 비고': '기관확인 필요', '특정자격 비고': None, '지역거주여부 비고': None, '선발방법 비고': None, '선발인원 비고': None, '자격제한 비고': '자세한 사항은 첨부파일 및 홈페이지 참고', '추천필요여부 비고': None, '제출서류 비고': '자세한 사항은 첨부파일 및 홈페이지 참고'},
        {'번호': 5, '상품명': '장학생', '운영기관명': '재단법인 조준장학재단', '운영기관구분': '기타', '상품구분': '장학금', '학자금유형구분': '기타', '모집시작일': '2024-11-13', '모집종료일': '2024-11-15', '홈페이지 주소': 'https://www.chojun.kr/', 
         '대학구분': ['특정대학'], '학년구분': ['대학4학기', '대학5학기'], '학과구분': ['특정학과'], '성적기준 상세내용': '○ 학점 4.0/4.3 이상', '소득기준 상세내용': '○ 242학기 학자금 지원구간 5구간 이내', '지원내역 상세내용': '○ 720만원 (생활비/연)', '특정자격 상세내용': '○ 경영학과 3학년 진급예정자 (2025학년도 1학기 기준) 1명○ 군 제대 후 복학생 지방 출신자 우대', '지역거주여부 상세내용': None, 
         '선발방법 상세내용': '○ 1차 서류전형/ 2차 면접전형', '선발인원 상세내용': '○ 각 학교당 1명', '자격제한 상세내용': '○ 타 재단 장학금 비수혜자 (국가 및 교내(성적우수)장학금은 제외)', '추천필요여부 상세내용': None, '제출서류 상세내용': '○ 장학생 지원 신청서○ 지도교수 추천서○ 자기소개서○ 성적증명서○ 재 학증명서○ 주민등록등본○ 학자금지원구간통지서○ 개인정보수집동의서', 
         '성적기준 비고': None, '소득기준 비고': None, '지원내역 비고': None, '특정자격 비고': '서 울대 공고 기준준', '지역거주여부 비고': None, '선발방법 비고': None, '선발인원 비고': None, '자격제한 비고': None, '추천필요여부 비고': '각 학교마다 추천여부부가 상이 할 수 있음', '제출서류 비고': '자세한 사항은 각 학교 장학팀 공지사항 참고'},
        {'번호': 6, '상품명': '장학생', '운영기관명': '(재)인제군장학회', '운영기관구분': '지자체(출자출연기관)', '상품구분': '장학금', '학자금유형구분': '지역연고', '모집시작일': '2025-01-06', '모집종료일': '2025-01-31', '홈페이지 주소': 'https://www.inje.go.kr', 
         '대학구분': ['4년제(5~6년제포함)', '전문대(2~3년제)'], '학년구분': [], '학과구분': [], '성적기준 상세내용': '○ (신입생)최종학력 학과 성적 중 과목별 석차 등급 3등급 이상이 전체 과목의 50% 이상○ (재학생)직전 학년 성적이 3.5점 이상. 각 학기당 12학점 이상(복학생은 직전 학년 2개 학기 평점 평균 3.5점 이상', '소득기준 상세내용': None, '지원내역 상세내용': '○ 500만원', '특정자격 상세내용': None, 
         '지역거주여부 상세내용': '○ 신청일 현재 관내에 주소를 두고 1년 이상 거주하고 있는 군민의 자녀 또는 본인○ 부모 또는 부양사실이 입증되는 보호자 중 한 명 이상이 인제군 관내에 거주 하면서 학업을 위하여 주소지를 이전한 학생', '선발방법 상세내용': None, '선발인원 상세내용': None, '자격제한 상세내용': '○ 인제군 인재육성기금 장학금과 중 복지원 불가○ 원격대학(사이버대학·방송통신대학)·야간대학·외국대학·학점은행제·전문학교·생활비를 지원받는 특수학교·대학원 제외○ 대학졸업예정자·휴학예정자(복학 시 신청가능) 제외○ 신청 학기 성적으 로 기 장학금을 지급받은 이력이 있는 자', 
         '추천필요여부 상세내용': None, '제출서류 상세내용': '○ 장학생지원서○ 개인정보 수집 이용제공 및 조회 동의서○ 부 또는 모의 주민등록등본(주소 기록 포함)○ 통장사본○ 가족관계증명서○ (신입생)합격증명서 또는 등록금 납부확인서·성적 입증 가능 서류○ (재학생·복학생)재학증명서·성적증명서○ (편입생)합격증명서·재학증명서·前학교 성적증명서', 
         '성적기준 비고': None, '소득기준 비고': None, '지원내역 비고': None, '특정자격 비고': None, '지역거주여부 비고': None, '선발방법 비고': '기관확인 필요', '선발인원 비고': '기관확인 필요', '자격제한 비고': '자세한 사항은 첨부파일 또는 홈페이지 참고', '추천필요여부 비고': None, '제출서류 비고': '자세한 사항은 첨부파일 또는 홈페이지 참고'},
        {'번호': 7, '상품명': '학업장학', '운영기관명': '우리다문화장학재단', '운영기관구분': '기타', '상품구분': '장학금', '학자금유형구분': '기타', '모집시작일': '2025-03-24', '모집종료일': '2025-04-18', '홈페이지 주소': 'http://www.woorifoundation.or.kr', 
         '대학구분': ['4년제(5~6년제포함)', '전문대(2~3년제)'], '학년구분': ['대학2학기', '대학3학기', '대학4학기', '대학5학기', '대학6학기', '대학7학기', '대학신입생'], '학과구분': [], '성적기준 상세내용': None, '소득기준 상세내용': '○ 2025년 기준 중위소득 100% 이하인 가구', '지원내역 상세내용': '○ 500만원(2회 분할 지급)', 
         '특정자격 상세내용': "○ 다문화가족 자녀○ 국내 2·3·4년제 대학교 재학생 및 휴학생○ 현재 학기(2025년 1학기) 포함 졸업까지 3학기 이상 남은 학생○ 매월 1회 이상 대학 장학생 서포터즈 '우리누리'활동에 필수 참여", '지역거주여부 상세내용': None, '선발방법 상세내용': '○ 서류평가 및 역량평가○ 면접 또는 전화 인터뷰(필요시)', '선발인원 상세내용': '○ 50명', '자격제한 상세내용': '○ 외국인 및 북한이탈 주민 지원불가○ 특기장학과 중복지원 불가능', '추천필요여부 상세내용': '○ 추천자격에 해당하는 자의 추천 필요○ 추천자격 : 소속대학 총장 및 학과장/다문화 및 사회 복지기관장/지자체 및 주민센터장', 
         '제출서류 상세내용': '○ 장학생 신청서 및 자기소개서○ 재학증명서○ 성적증명서(신입생 제외)○ 장학생 추천서○ 주민등록등본○ 가족관계증명서○ 다문화 학생임을 입증할 수 있는 서류 1부○ 법정 저소득 증빙서류(해당자)○ 차상위 본인부담경감대상자 증명서(해당 자)○ 건강보험자격확인서(해당자)○ 건강보험료 납부확인서(해당자)○ 자원봉사활동 실적확인서(해당자)○ 수상 실적 자료(해당자)', 
         '성적기준 비고': None, '소득기준 비고': None, '지원내역 비고': None, '특정자격 비고': None, '지역거주여부 비고': None, '선발방법 비고': None, '선발인원 비고': None, '자격제한 비고': None, '추천필요여부 비고': '대학교 행정 실무자 추천 불가', '제출서류 비고': '자세한 사항은 첨부자료 참고'},
        {'번호': 8, '상품명': '특기장학', '운영기관명': '우리다문화장학재단', '운영기관구분': '기타', '상품구분': '장학금', '학자금유형구분': '특기자', '모집시작일': '2025-03-24', '모집종료일': '2025-04-18', '홈페이지 주소': 'http://www.woorifoundation.or.kr', 
         '대학구분': ['4년제(5~6년제포함)', '기술대학', '원격대학', '일반대학원', '전문대(2~3년제)', '전문대학원', '제한없음', '학점은행제 대학', '해외대학'], '학년구분': ['대학2학기', '대학3학기', '대학4학기', '대학5학기', '대학6학기', '대학7학기', '대학8학기이상', '대학신입생', '연령제한', '제한없음'], '학과구분': ['공학계열', '교육계열', '사회계열', '예체능계열', '의약계열', '인문계열', '자연계열', '제한없음'], 
         '성적기준 상세내용': None, '소득기준 상세내용': None, '지원내역 상세내용': '○ 500만원', '특정자격 상세내용': "○ 특기 및 재능 보유 다문화가족 자녀(8~30세: 1996년생~2018년생)○ 예·체능 및 어학 특기자/자격·기술 보유자/직업·진로 특기자 등○ 최근 3년 이내에 전국 규모 이상의 대회 입상실적 또는 이에 상응하는 특기 및 재능 관련 실적자료 제출이 가능해야 함○ 학교 재학 여부 관계없음 (졸업생 및 학교 밖 청소년 신청가능)", '지역거주여부 상세내용': None, 
         '선발방법 상세내용': '○ 서류평가 및 역량평가○ 면접 또는 전 화 인터뷰(필요시)', '선발인원 상세내용': '○ 30명', '자격제한 상세내용': '○ 부모 모두 외국 국적을 가진 가족 및 북한이탈주민 지원불가○ 학업장학과 중복지원 불가능', '추천필요여부 상세내용': '○ 추천자격에 해당하는 자의 추천 필요○ 추천자격 : 소속대학 학교장 및 총장(지도교수 및 학과장 포함)/다문화 및 사회 복지기관장/지자체 및 주민센터장/특기·재능 관련 전문기관장', 
         '제출서류 상세내용': '○ 장학생 신청서 및 자기소개서○ 재학증명서 또는 재직증명서/졸업증명서 또는 경력증명서○ 장학생 추천서○ 주민등록등본○ 가족관계증명서○ 다문화 학생임을 입증할 수 있는 서류 1 부○ 수상 실적 자료 또는 경력 관련 포트폴리오(수상확인서·상장 사본·관련기사 스크랩 등)○ 법정 저소득 증빙서류(해당자)○ 차상위 본인부담경감대상자 증명서(해당자)○ 건강보험자격확인서(해당자)○ 건강 보험료 납부확인서(해당자)○ 자원봉사활동 실적확인서(해당자)', 
         '성적기준 비고': None, '소득기준 비고': None, '지원내역 비고': None, '특정자격 비고': None, '지역거주여부 비고': None, '선발방법 비고': None, '선발인원 비고': None, '자격제한 비고': None, '추천필요여부 비고': None, '제출서류 비고': '자세한 사항은 첨부자료 참고'},
        {'번호': 9, '상품명': '삼원지헌장학생', '운영기관명': '지헌장학재단', '운영기관구분': '기타', '상품구분': '장학금', '학자금유형구분': '기타', '모집시작일': '2025-03-04', '모집종료일': '2025-03-25', '홈페이지 주소': 'http://www.jiheonsf.or.kr', 
         '대학구분': ['4년제(5~6년제포함)'], '학년구분': ['대학5학기', '대학6학기', '대학7학기', '대학8학기이상'], '학과구분': ['예체능계열'], '성적기준 상세내용': '○ 최근1년 평균성적 B+ 이상 (3.5/4.5 이상)', '소득기준 상세내용': '○ 2025년 1학기 기준 한국장학재단 학자금 지원구간 7구간 이내의 학생', '지원내역 상세내용': '○ 100만원', 
         '특정자격 상세내용': '○ 4년제 대학교 3~4학년 재학생○ 시각디자인 전공자 및 판화학과 전공', '지역거주여부 상세내용': None, '선발방법 상세내용': '○ 1차 서류전형 ○ 2차 면접전형 (필요시)', '선발인원 상세내용': '○ 44명 내외', '자격제한 상세내용': '○ 기업체 학술연수 및 입사 조건부 장학금을 받는 자○ 장학금을 수령한 학기에는 휴학을 할 수 없으며 휴학의 경우 장학금을 반환해야 함', 
         '추천필요여부 상세내용': None, '제출서류 상세내용': '○ 장학생 선발원서○ 자기소개 및 학업계획서○ 주민등록등본 또는 가족관계증명서○ 학자금 지원구간 통지서○ 성적증명서○ 통장사본(본인 또는 보호자)○ 개인정보 수집·이용·제공 동의서○ 입상증명서(가점 요인으로 반영)', 
         '성적기준 비고': None, '소득기준 비고': None, '지원내역 비고': '생활비(학 자금 및 디자인 재료비)로 타 장학금과 이중수혜 가능', '특정자격 비고': None, '지역거주여부 비고': None, '선발방법 비고': None, '선발인원 비고': None, '자격제한 비고': None, '추천필요여부 비고': None, '제출서류 비고': '자세한 사항은 첨부자료 참고'},
        {'번호': 10, '상품명': '풍육장학생', '운영기관명': '풍육장학회', '운영기관구분': '기타', '상품구분': '장학금', '학자금유형구분': '기타', '모집시작일': '2025-01-27', '모집종료일': '2025-02-17', '홈페이지 주소': 'http://cafe.naver.com/choscholarship', 
         '대학구분': ['4년제(5~6년제포함)', '해외대학'], '학년구분': ['대학2학기', '대학3학기', '대학4학기', '대학5학기', '대학6학기', '대학7학기', '대학8학기이상', '대학신입생'], '학과구분': ['공학계열', '교육계열', '사회계열', '예체능계열', '의약계열', '인문계열', '자연계열', '제한없음'], 
         '성적기준 상세내용': '○ 성적이 우수한 자', '소득기준 상세내용': None, '지원내역 상세내용': None, '특정자격 상세내용': '○ 풍양조씨인 자○ 성적이 우수하고 행실이 바른 정규 4년제 대학 신입생 및 재학생 또는 해외유 학생', '지역거주여부 상세내용': None, '선발방법 상세내용': None, '선발인원 상세내용': '○ 00명', 
         '자격제한 상세내용': '○ 1세대 1자녀 원칙○ 타처에서 장학금을 받고 있는 학생 은 신청 불가능○ 수능성적 없이 수시전형에 합격한 자는 신청할 수 없음○ 한번 수혜 받은 학생은 재신청 불가○ 전문대/대학원생 제외', '추천필요여부 상세내용': None, 
         '제출서류 상세내용': '○ 장학 금 수혜원서(본회 소정양식) 1통○ 성적증명서 (재적학교 발행)○ 신입생 : 수능시험성적통지표·대학합격통지표 각1통○ 재학생 : 소속대학의 성적증명서·재학증명서 각 1통○ 가족관계증명서 1통○ 기초생활수혜대상자 증명서 (해당자)○ 장애인증명서(해당자)○ 소속학교와 자신에 관한 소개서(해외 유학생의 경우) 1통○ 효행상수상확인서 (해당자)', 
         '성적기준 비고': None, '소득기준 비고': None, '지원내역 비고': '기관확인 필요', '특정자격 비고': None, '지역거주여부 비고': None, '선발방법 비고': '기관확인 필요', '선발인원 비고': None, '자격제한 비고': '이 외 자세한 사항은 첨부파일 참고', '추천필요여부 비고': None, '제출서류 비고': '자세한 사항은 첨부파일 참고'}
    ]

    # DB에서 지역명-ID 맵 가져오기
    sido_map_from_db, sigungus_map_from_db, id_map_from_db = get_region_maps_from_db()

    # --- Step 1: 데이터 변환 (Transformer) ---
    print("\n[Step 1] Transformer를 사용하여 Pydantic 객체로 변환 중...")
    
    scholarships, all_grade_criteria, all_income_criteria, all_general_criteria, all_region_links = transform_data(
        cleaned_data=sample_cleaned_data,
        sido_map=sido_map_from_db,
        all_sigungus_map=sigungus_map_from_db,
        id_to_region_map=id_map_from_db
    )
        
    print(f"✅ 총 {len(scholarships)}개의 장학금 객체 변환 완료.")


    # --- 변환된 객체 구조 로그 출력 ---
    print("\n--- 변환된 Scholarship 객체 구조 (첫 2개) ---")
    for i, s in enumerate(scholarships[:2]): # 첫 2개의 객체만 출력 (너무 길어지는 것을 방지)
        print(f"\n--- Scholarship {i+1} (Original ID: {s.original_id}) ---")
        print(s.model_dump_json(indent=2)) # Pydantic 객체를 JSON 문자열로 변환하여 출력

    print("\n--- 변환된 GradeCriterion 객체 구조 (첫 2개) ---")
    for i, gc in enumerate(all_grade_criteria[:2]):
        print(f"\n--- GradeCriterion {i+1} (Scholarship ID: {gc.scholarship_id}) ---")
        print(gc.model_dump_json(indent=2))

    print("\n--- 변환된 IncomeCriterion 객체 구조 (첫 2개) ---")
    for i, ic in enumerate(all_income_criteria[:2]):
        print(f"\n--- IncomeCriterion {i+1} (Scholarship ID: {ic.scholarship_id}) ---")
        print(ic.model_dump_json(indent=2))

    print("\n--- 변환된 GeneralCriterion 객체 구조 (첫 2개) ---")
    for i, gnc in enumerate(all_general_criteria[:2]):
        print(f"\n--- GeneralCriterion {i+1} (Scholarship ID: {gnc.scholarship_id}) ---")
        print(gnc.model_dump_json(indent=2))
    print("\n--- 변환된 ScholarshipRegion 객체 구조 (전체) ---")
    grouped_links = {}
    for link in all_region_links:
        if link.scholarship_id not in grouped_links:
            grouped_links[link.scholarship_id] = []
        grouped_links[link.scholarship_id].append(link)

    for scholarship_id, links in sorted(grouped_links.items()):
        print(f"\n--- Scholarship ID: {scholarship_id} ---")
        for link in sorted(links, key=lambda x: x.region_id):
            print(link.model_dump_json(indent=2))

    # --- 변환된 객체들을 scholarship_id 기준으로 그룹화 ---
    grouped_grades = {s.original_id: [] for s in scholarships}
    for item in all_grade_criteria: grouped_grades[item.scholarship_id].append(item)
    
    grouped_incomes = {s.original_id: [] for s in scholarships}
    for item in all_income_criteria: grouped_incomes[item.scholarship_id].append(item)
    
    grouped_generals = {s.original_id: [] for s in scholarships}
    for item in all_general_criteria: grouped_generals[item.scholarship_id].append(item)
    
    grouped_regions = {s.original_id: [] for s in scholarships}
    for item in all_region_links: grouped_regions[item.scholarship_id].append(item)

    # --- Step 2: 데이터 정합성 검증 (Validator) ---
    print("\n[Step 2] Validator를 사용하여 데이터 정합성 검증 중...")
    
    valid_scholarships = []
    valid_grade_criteria = []
    valid_income_criteria = []
    valid_general_criteria = []

    for scholarship in scholarships:
        # <--- DB id가 없으므로 임시 ID인 original_id를 사용
        temp_s_id = scholarship.original_id
        
        related_grades = [gc for gc in all_grade_criteria if gc.scholarship_id == temp_s_id]
        related_incomes = [ic for ic in all_income_criteria if ic.scholarship_id == temp_s_id]
        related_generals = [gc for gc in all_general_criteria if gc.scholarship_id == temp_s_id]

        is_valid = validate_scholarship_data(
            scholarship=scholarship,
            grade_criteria=grouped_grades.get(temp_s_id, []),
            income_criteria=grouped_incomes.get(temp_s_id, []),
            general_criteria=grouped_generals.get(temp_s_id, []),
            scholarship_regions=grouped_regions.get(temp_s_id, []),
            id_to_region_map=id_map_from_db
        )
        
        if is_valid:
            valid_scholarships.append(scholarship)
            valid_grade_criteria.extend(related_grades)
            valid_income_criteria.extend(related_incomes)
            valid_general_criteria.extend(related_generals)

    # --- Step 3: 최종 결과 ---
    print("\n[Step 3] 최종 처리 결과 요약")
    print("-" * 30)
    print(f"총 {len(sample_cleaned_data)}개 데이터 처리 시도")
    print(f"  - Pydantic 변환 성공: {len(scholarships)}개")
    print(f"  - 최종 정합성 검증 통과: {len(valid_scholarships)}개")
    print("-" * 30)


    # --- Step 4: DB 저장 (Loader) ---
    # <--- 저장 대상 출력 시 original_id 사용
    for s in valid_scholarships:
        print(f"  -> 저장 대상: Scholarship Original ID: {s.original_id}, Name: {s.product_name}")

    print("파이프라인 테스트 종료")