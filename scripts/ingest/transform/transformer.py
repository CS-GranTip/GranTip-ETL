from typing import Tuple, List, Dict, Any

from pydantic import ValidationError

from models.scholarship import Scholarship
from models.criterion.grade_criterion import GradeCriterion
from models.criterion.income_criterion import IncomeCriterion
from models.criterion.general_criterion import GeneralCriterion
from models.scholarship_region import ScholarshipRegion

from .parsers.grade_parser import extract_grade_criteria
from .parsers.income_parser import extract_income_criteria
from .parsers.selection_parser import parse_selection_personnel
from .parsers.restriction_parser import check_duplicate_support_restriction
from .parsers.region_parser import extract_region_links

def transform_data(
        cleaned_data: List[Dict[str, Any]],
        category_id_map: Dict[str, int],
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
            university_keywords = row.get('대학구분', [])
            university_category_ids = [category_id_map[keyword] for keyword in university_keywords if keyword in category_id_map]
            scholarship_data['university_category_ids'] = university_category_ids
            if 'university_category' in scholarship_data:
                del scholarship_data['university_category']
                
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
