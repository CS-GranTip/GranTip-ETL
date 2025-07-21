import re
import json
from typing import List, Optional, Tuple, Dict, Any

# --- 각 필드별 List[str] 분리 로직 ---

def parse_university_category(text: Optional[str]) -> List[str]:
    """
    '대학구분' 필드의 붙어있는 문자열을 리스트로 분리
    (예: '4년제(5~6년제포함)전문대(2~3년제)' -> ['4년제(5~6년제포함)', '전문대(2~3년제)'])
    """
    if not text:
        return []
    
    patterns = [
        # 1순위
        r'4년제\(5~6년제포함\)',
        r'전문대\(2~3년제\)',
        r'학점은행제 대학',

        # 2순위
        r'\w+대학원',  # '일반대학원', '전문대학원' 등
        r'\w+대학',   # '기술대학', '원격대학', '해외대학' 등

        # 3순위
        '제한없음'
    ]

    # 패턴들을 OR('|')로 연결하여 하나의 마스터 패턴 생성
    master_pattern = '|'.join(patterns)

    # 마스터 패턴과 일치하는 모든 부분 리스트로 반환
    return re.findall(master_pattern, text)

def parse_grade_category(text: Optional[str]) -> List[str]:
    """
    '대학구분' 필드의 붙어있는 문자열을 리스트로 분리
    (예: '대학2학기대학3학기' -> ['대학2학기', '대학3학기'])
    """
    if not text:
        return []
    
    # 긴 단위를 앞에 두어 짧은 단위가 먼저 매칭되는 것을 방지
    patterns = [
        # 1순위
        r'석사신입생\(1학기\)',
        '대학8학기이상',
        '석사2학기이상',

        # 2순위
        r'대학\d학기',     # '대학2학기', '대학3학기' 등
        '대학신입생',
        '박사과정',

        # 3순위
        '연령제한',
        '제한없음'
    ]

    master_pattern = '|'.join(patterns)

    return re.findall(master_pattern, text)

def parse_department_category(text: Optional[str]) -> List[str]:
    """
    '학과구분' 필드의 붙어있는 문자열을 리스트로 분리
    정의된 키워드 목록에 기반하여 분리
    (예: '공학계열교육계열' -> ['공학계열', '교육계열'])
    """
    if not text:
        return []
    
    # '학과구분'에 나타나는 모든 키워드 정의
    keywords = [
        '공학계열', '교육계열', '사회계열', '예체능계열',
        '의약계열', '인문계열', '자연계열', '특정학과', '제한없음'
    ]

    # 키워드들을 OR('|')로 연결하여 패턴 생성
    pattern = '|'.join(keywords)

    return re.findall(pattern, text)


# --- 비고(※) 분리 로직 ---

def preprocess_text_field(text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    텍스트 필드에서 내용 뒤에 따라오는 비고(※)만 분리합니다.
    """
    if not text:
        return None, None
    
    clean_text = text.strip()

    # '※'가 맨 앞이 아니고, 중간에 있을 때만 분리
    if '※' in clean_text and not clean_text.startswith('※'):
        parts = clean_text.split('※', 1)
        detail = parts[0].strip()
        notes = parts[1].strip()
        return detail if detail else None, notes if notes else None
    else:
        # 그 외의 경우 (※가 없거나, 맨 앞에 오는 경우)에는 전체를 detail로 취급
        return clean_text if clean_text else None, None
    

# --- 상수 ---
CATEGORY_PARSERS = {
    '대학구분': parse_university_category,
    '학년구분': parse_grade_category,
    '학과구분': parse_department_category
}
FIELDS_WITH_NOTES = [
    "성적기준 상세내용", "소득기준 상세내용", "지원내역 상세내용", "특정자격 상세내용", "지역거주여부 상세내용", 
    "선발방법 상세내용", "선발인원 상세내용", "자격제한 상세내용", "추천필요여부 상세내용", "제출서류 상세내용"
]



# --- 메인 함수 ---

def clean_raw_data(raw_data_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    수집된 raw 데이터 리스트 전체의 구조적, 내용적 정제 수행
    """
    cleaned_rows = []

    for row in raw_data_rows:
        processed_row = row.copy()

        # 상품명과 운영기관명 결합
        scholarship_name = f"[{row.get('운영기관명', '')}]{row.get('상품명', '')}"
        processed_row['상품명'] = scholarship_name
        del processed_row['운영기관명']

        # 모든 필드에 대해 '해당없음' -> None 변환 & 양옆 공백 제거
        for key, value in processed_row.items():
            if isinstance(value, str):
                stripped_value = value.strip()
                processed_row[key] = None if stripped_value in ['해당없음', ''] else stripped_value

        # URL 오타 교정 로직
        url_key = '홈페이지 주소'
        if url_key in processed_row and isinstance(processed_row[url_key], str):
            processed_row[url_key] = processed_row[url_key].replace('http//', 'http://')

        # 비고 분리
        for field_name in FIELDS_WITH_NOTES:
            detail, notes = preprocess_text_field(processed_row.get(field_name))
            processed_row[field_name] = detail
            # 새로운 '비고' 키 생성
            notes_key = field_name.replace(' 상세내용', ' 비고')
            processed_row[notes_key] = notes

        # 카테고리 필드 분리
        for field_name, parser_function in CATEGORY_PARSERS.items():
            if field_name in processed_row:
                processed_row[field_name] = parser_function(processed_row.get(field_name))

        


        cleaned_rows.append(processed_row)

    return cleaned_rows

# --- 데이터 파싱 테스트 실행 부분 ---
if __name__ == "__main__":
    # 원본 JSON 데이터
    raw_json_data = {
        "번호": 1,
        "상품명": "행복나눔 장학생",
        "운영기관명": "광주남구장학회",
        "운영기관구분": "지자체(출자출연기관)",
        "상품구분": "장학금",
        "학자금유형구분": "지역연고",
        "모집시작일": "2024-09-23",
        "모집종료일": "2024-10-11",
        "홈페이지 주소": "https://namgu.gwangju.kr",
        "대학구분": "4년제(5~6년제포함)",
        "학년구분": "대학2학기대학3학기대학4학기대학5학기대학6학기대학7학기대학8학기이상대학신입생",
        "학과구분": "공학계열교육계열사회계열예체능계열의약계열인문계열자연계열제한없음",
        "성적기준 상세내용": "○ 직전학기 12학점 이상 취득하고 성적 평균 2.75 이상인 자 (4.3만점은 2.6이상)",
        "소득기준 상세내용": "○ 2024년도 기준 중위소득 100% 이하인 가구※ 직계가족의 3개월 평균국민건강보험료 산정",
        "지원내역 상세내용": "○ 1인당 100만원※ 생활비 지원",
        "특정자격 상세내용": "○ 공고일 현재 신청 학생 또는 학생의 부모가 광주광역시 남구에 주민등록상 1년 이상 주소를 두고 이고 유형별 자격과 요건을 충족하는 자",
        "지역거주여부 상세내용": "○ 보호자 또는 본인이 선발 공고일 현재 주민등록상 주소지가 광주광역시 남구로 1년 이상 두고 신 청 요건을 갖춘 자",
        "선발방법 상세내용": "○ 서류심사 (사무국) : 제출서류 신청요건 충족 및 직전학기 성적 등 확인○ 심사의결 (장학생 선발 심사위원회)○ 최종선정자 발표○ 선 발결과 : 개별 안내 및 홈페이지 게시",
        "선발인원 상세내용": "○ 12명",
        "자격제한 상세내용": "○ 기술대학○ 2년 미만 교육과정의 각종 학교○ 평생교육법에 의거 설립한 학교○ 최근 2년 남구장학회 장학생으로 선발된 자○ 휴학(등록 휴학 포함) / 제적 / 자퇴 / 졸업 등 학기 미등록자※ 자세한 사항 공고 참조",
        "추천필요여부 상세내용": "해당없음",
        "제출서류 상세내용": "○ 장학생 신청서○ 주민등록표등본○ 학생 명의의 가족관계증명서○ 건강보험 자격확인서○ 건강보험료 납부확인서○ 2024년 1학기 성적증명서○ 재학증명서○ 2학기 등록금 납입증명서○ 개인정보 수집·이용·제공 및 조회 동의서○ 통장 사본○ 가정환경 세대구성 관련증명서 (해당자)※ 자세한 사항 공고문 참조"
    }

    # clean_raw_data 함수는 List[Dict]를 인자로 받으므로, 단일 딕셔너리를 리스트로 감싸줍니다.
    raw_data_list = [raw_json_data]

    print("--- 원본 데이터 ---")
    print(json.dumps(raw_json_data, indent=4, ensure_ascii=False))

    # 데이터 정제 함수 호출
    cleaned_data_list = clean_raw_data(raw_data_list)

    print("\n--- data_parser를 거친 후의 데이터 ---")
    if cleaned_data_list:
        print(json.dumps(cleaned_data_list[0], indent=4, ensure_ascii=False))
    else:
        print("정제된 데이터가 없습니다.")

