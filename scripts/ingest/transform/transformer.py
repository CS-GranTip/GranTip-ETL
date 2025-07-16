from typing import Tuple, Optional, List, Dict, Any

from pydantic import ValidationError

from models.scholarship import Scholarship
from models.criterion.grade_criterion import GradeCriterion
from models.criterion.income_criterion import IncomeCriterion

from .validator import validate_scholarship_data
from .grade_parser import extract_grade_criteria
from .income_parser import extract_income_criteria
import re

def parse_selection_personnel(text: Optional[str]) -> Tuple[Optional[int], Optional[Dict[str, int]]]:
    """
    OpenAPI의 선발인원 상세내용을 파싱하여 구조화된 데이터를 반환합니다.
    '○' 형식으로 구분된 경우를 우선 처리하며, 기존 패턴도 유지합니다.
    예: "○ 12명 ○ 국내: 20명 총 32명" -> (32, {'국내': 20})
    """
    if text is None:
        return None, None
    
    categorized: Dict[str, int] = {}
    
    # '○'으로 분할하여 각 그룹 처리
    groups = re.split(r'○', text.strip())
    
    for group in groups:
        group = group.strip()
        if not group:
            continue
        # 각 그룹에서 숫자와 '명' 추출
        match = re.search(r'(\d+)\s*명', group)
        if match:
            num = int(match.group(1))
            # 카테고리 추출: 숫자 앞의 텍스트를 키로 사용 
            category_text = group[:match.start()].strip().rstrip(':')  # 콜론 제거
            if category_text:
                key = category_text.strip().lower().replace(' ', '_')
                # '총' 키를 'total'로 매핑
                if key == '총':
                    key = 'total'
                categorized[key] = num
            # 카테고리 없으면 total로 통합 (기존 값에 더함)
            else:
                if 'total' in categorized:
                    categorized['total'] += num
                else:
                    categorized['total'] = num
    
    # 총 인원 직접 추출 (우선 적용, 오버라이드)
    total_match = re.search(r'총\s*(\d+)\s*명', text)
    if total_match:
        total = int(total_match.group(1))
    elif categorized:
        total = sum(categorized.values())
    else:
        total = None
    
    # 추가: 괄호 안 / 구분된 카테고리 파싱 (콜론 없음)
    inner_match = re.search(r'\(([^)]+)\)', text)
    if inner_match:
        inner = inner_match.group(1)
        inner_pattern = r'/?\s*([^/]+?)\s*(\d+)\s*명'
        inner_matches = re.findall(inner_pattern, inner)
        for cat, num in inner_matches:
            key = cat.strip().lower().replace(' ', '_')
            categorized[key] = int(num)
    
    if not categorized:
        return None, None
    
    return total, categorized if categorized else None

def check_duplicate_support_restriction(text: Optional[str]) -> bool:
    """자격제한 상세내용을 분석하여 중복수혜 제한 여부를 반환합니다."""
    if not text:
        return False

    # 1. '생활비' 장학금은 중복수혜가 허용되는 경우가 많으므로 예외 처리
    if '생활비' in text and ('가능' in text or '중복지원 가능' in text):
        return False

    # 2. 제한을 나타내는 핵심 키워드 목록
    restriction_keywords = [
        '중복', '이중', '비수혜자', '수혜자 제외',
        '타 장학금', '타장학금', '다른 장학금', '타처에서',
        '등록금 범위', '학비 면제', '전액 지원',
        '기수혜자',   '재신청', '수여자', '지원받는 자'
    ]

    # 명시적으로 '허용'이나 '가능'을 언급하는지 확인 ("중복 수혜 가능" 같은 문장을 False로 처리하기 위함)
    if '중복' in text and '가능' in text:
        return False
    if '중복' in text and '허용' in text:
        return False

    # 제한 키워드가 하나라도 포함되면 True로 판단
    if any(keyword in text for keyword in restriction_keywords):
        return True

    return False


def transform_data(
        cleaned_data: List[Dict[str, Any]]
) -> Tuple[List[Scholarship], List[GradeCriterion], List[IncomeCriterion]]:
    """
    정제된 딕셔너리 리스트를 최종 Scholarship Pydantic 모델 리스트로 변환합니다.
    """
    scholarship_models = []
    grade_criteria_models = []
    income_criteria_models = []

    for row in cleaned_data:
        try:
            scholarship_data = row.copy()
            scholarship_id = row.get("번호")
            
            # 각 기준별 Parser 호출하여 구조화된 객체 생성
            grade_criterias = extract_grade_criteria(
                scholarship_id=scholarship_id,
                raw_text=row.get("성적기준 상세내용")
            )
            income_criterias = extract_income_criteria(
                scholarship_id=scholarship_id,
                raw_text=row.get("소득기준 상세내용")
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

        except ValidationError as e:
            print(f"데이터 검증 실패 (ID: {row.get('번호', 'N/A')}): {e}")
        except Exception as e:
            print(f"알 수 없는 에러 발생 (ID: {row.get('번호', 'N/A')}): {e}")

    return scholarship_models, grade_criteria_models, income_criteria_models



    

if __name__ == "__main__":
    # --- 테스트 환경 설정 --- (추후 수정될 예정)
    print("데이터 변환 및 검증 파이프라인 테스트 시작")

    # 1. 테스트용 샘플 데이터 (cleaner를 거친 상태라고 가정)
    sample_cleaned_data = [
        # Case 1: 성공 케이스
        {
            "번호": 1, "상품명": "미래인재 장학금", "운영기관명": "대한장학재단",
            "운영기관구분": "재단법인", "상품구분": "장학금", "학자금유형구분": "성적우수",
            "모집시작일": "2025-09-01", "모집종료일": "2025-09-30",
            "성적기준 상세내용": "직전학기 평점 3.5/4.5 이상", "추천필요여부 상세내용": "지도교수 추천서 필요",
            "자격제한 상세내용": "타 장학금과 중복수혜 불가"
        },
        # Case 2: Validator에서 실패할 케이스
        {
            "번호": 2, "상품명": "논리오류 장학금", "운영기관명": "오류재단",
            "운영기관구분": "기타", "상품구분": "장학금", "학자금유형구분": "성적우수",
            "모집시작일": "2025-10-15", "모집종료일": "2025-10-01",  # 오류: 시작일 > 종료일
            "성적기준 상세내용": None,  # 오류: 성적우수인데 기준 없음
        }
    ]

    # --- Step 1: 데이터 변환 (Transformer) ---
    print("\n[Step 1] Transformer를 사용하여 Pydantic 객체로 변환 중...")
    
    scholarships, all_grade_criteria, all_income_criteria = transform_data(sample_cleaned_data)
    
    print(f"✅ 총 {len(scholarships)}개의 장학금 객체 변환 완료.")


    # --- Step 2: 데이터 정합성 검증 (Validator) ---
    print("\n[Step 2] Validator를 사용하여 데이터 정합성 검증 중...")
    
    valid_scholarships = []
    valid_grade_criteria = []
    valid_income_criteria = []

    for scholarship in scholarships:
        s_id = scholarship.id
        
        related_grades = [gc for gc in all_grade_criteria if gc.scholarship_id == s_id]
        related_incomes = [ic for ic in all_income_criteria if ic.scholarship_id == s_id]

        is_valid = validate_scholarship_data(
            scholarship=scholarship,
            grade_criteria=related_grades,
            income_criteria=related_incomes
        )
        
        if is_valid:
            valid_scholarships.append(scholarship)
            valid_grade_criteria.extend(related_grades)
            valid_income_criteria.extend(related_incomes)

    # --- Step 3: 최종 결과 ---
    print("\n[Step 3] 최종 처리 결과 요약")
    print("-" * 30)
    print(f"총 {len(sample_cleaned_data)}개 데이터 처리 시도")
    print(f"  - Pydantic 변환 성공: {len(scholarships)}개")
    print(f"  - 최종 정합성 검증 통과: {len(valid_scholarships)}개")
    print("-" * 30)


    # --- Step 4: DB 저장 (Loader) ---
    for s in valid_scholarships:
        print(f"  -> 저장 대상: Scholarship ID: {s.id}, Name: {s.product_name}")

    print("파이프라인 테스트 종료")