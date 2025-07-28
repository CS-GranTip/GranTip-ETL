import re
import json
from typing import List, Optional, Tuple, Dict, Any

# --- 각 필드별 List[str] 분리 로직 ---

def parse_university_category(text: Optional[str]) -> List[str]:
    """
    '대학구분' 필드를 정렬 및 이스케이프 처리된 키워드와 재귀 로직을 이용해
    정확하게 분리하는 최종 버전입니다.
    """
    if not text:
        return []

    # 분리에 사용할 모든 키워드를 정의합니다.
    keywords = [
        '4년제(5~6년제포함)', '전문대(2~3년제)', '학점은행제 대학', '일반대학원',
        '전문대학원', '기술대학', '원격대학', '해외대학', '특정대학', '제한없음'
    ]

    # 키워드를 길이순으로 내림차순 정렬하고, 각 키워드의 특수 문자를 이스케이프 처리합니다.
    keywords.sort(key=len, reverse=True)
    escaped_keywords = [re.escape(k) for k in keywords]
    master_pattern = '|'.join(escaped_keywords)
    
    # -------------------------------------------------------------

    # 내부 재귀 함수 정의
    memo = {} # 중복 계산을 피하기 위한 메모이제이션
    def _recursive_parse(sub_text: str) -> Optional[List[str]]:
        if not sub_text:
            return []
        
        # 이미 계산한 결과가 있으면 즉시 반환
        if sub_text in memo:
            return memo[sub_text]

        # 현재 문자열의 시작 부분과 일치하는 가장 긴 키워드를 찾음
        match = re.match(r'(' + master_pattern + ')', sub_text)
        
        if match:
            token = match.group(1)
            # 매칭된 토큰은 원래의 키워드여야 하므로, 이스케이프되지 않은 버전을 찾습니다.
            # 이 부분은 re.match가 반환하는 값은 원본 문자열이므로, 추가 변환이 필요 없습니다.
            
            remaining_text = sub_text[len(token):]
            remaining_result = _recursive_parse(remaining_text)

            if remaining_result is not None:
                # 성공 경로를 메모이제이션하고 결과 반환
                memo[sub_text] = [token] + remaining_result
                return memo[sub_text]
        
        # 실패 경로를 메모이제이션
        memo[sub_text] = None
        return None

    # 메인 함수 로직
    result = _recursive_parse(text.strip())
    return result if result is not None else [text]

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
    텍스트 필드에서 내용(detail)과 비고(notes)를 분리합니다.
    분리된 비고 내에 추가적인 '※'가 있다면 쉼표로 변환합니다.
    """
    if not text:
        return None, None
    
    clean_text = text.strip()

    detail = None
    notes = None

    # '※'가 맨 앞이 아니고, 중간에 있을 때만 분리
    if '※' in clean_text and not clean_text.startswith('※'):
        parts = clean_text.split('※', 1)
        detail = parts[0].strip()
        
        notes_raw = parts[1].strip()
        if notes_raw:
            # 비고 부분에 남아있는 '※'를 ', '로 변환
            # 여러 개의 '※'와 공백을 깔끔하게 처리하기 위해 split 후 join 사용
            notes_parts = [p.strip() for p in notes_raw.split('※') if p.strip()]
            notes = ", ".join(notes_parts)

    else:
        # 그 외의 경우 (※가 없거나, 맨 앞에 오는 경우)에는 전체를 detail로 취급
        detail = clean_text

    return (detail if detail else None, notes if notes else None)
    
# --- url 정제 ---
def clean_url(url: Optional[str]) -> Optional[str]:
    """
    URL 문자열을 정제하고 표준 형식으로 변환합니다.

    - None 또는 빈 문자열은 None으로 반환
    - 'htps://' 또는 'http//' 같은 일반적인 오타 수정
    - 'http' 스킴이 없으면 'https://'를 기본값으로 추가
    """
    if not url or not isinstance(url, str):
        return None
    
    # 양쪽 공백 제거 및 소문자 변환
    cleaned_url = url.strip().lower()
    
    # 일반적인 오타 수정
    cleaned_url = cleaned_url.replace('htps://', 'https://')
    cleaned_url = cleaned_url.replace('http//', 'http://')

    # 스킴이 없는 경우 https:// 추가
    if not cleaned_url.startswith(('http://', 'https://')):
        cleaned_url = f"https://{cleaned_url}"
    
    return cleaned_url
    

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

PROVIDER_TYPE_MAP = {
    "지자체(출자출연기관)": "LOCAL_GOV",
    "공공기관": "PUBLIC_ORG",
    "기타": "ETC",
}

PRODUCT_TYPE_MAP = {
    "장학금": "SCHOLARSHIP",
    "학자금": "LOAN",
}

SCHOLARSHIP_CATEGORY_MAP = {
    "지역연고": "LOCAL",
    "특기자": "SPECIALTY",
    "성적우수": "GRADE",
    "소득구분": "INCOME",
    "장애인": "DISABILITY",
    "기타": "ETC",
}



# --- 메인 함수 ---

def clean_raw_data(raw_data_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    수집된 raw 데이터 리스트 전체의 구조적, 내용적 정제 수행
    """
    cleaned_rows = []

    for row in raw_data_rows:
        processed_row = row.copy()

        # 상품명과 운영기관명 결합
        scholarship_name = f"[{row.get('운영기관명', '')}] {row.get('상품명', '')}"
        processed_row['상품명'] = scholarship_name

        # 모든 필드에 대해 '해당없음' -> None 변환 & 양옆 공백 제거
        for key, value in processed_row.items():
            if isinstance(value, str):
                stripped_value = value.strip()
                processed_row[key] = None if stripped_value in ['해당없음', ''] else stripped_value

        # Enum 필드 변환
        processed_row['운영기관구분'] = PROVIDER_TYPE_MAP.get(processed_row.get('운영기관구분'))
        processed_row['상품구분'] = PRODUCT_TYPE_MAP.get(processed_row.get('상품구분'))
        processed_row['학자금유형구분'] = SCHOLARSHIP_CATEGORY_MAP.get(processed_row.get('학자금유형구분'))

        # URL 정제
        processed_row['홈페이지 주소'] = clean_url(row.get('홈페이지 주소'))

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

