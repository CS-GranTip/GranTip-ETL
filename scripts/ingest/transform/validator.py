import re
import logging
from typing import List, Dict, Any
from models.scholarship import Scholarship
from models.criterion.grade_criterion import GradeCriterion
from models.criterion.income_criterion import IncomeCriterion
from models.criterion.general_criterion import GeneralCriterion
from models.scholarship_region import ScholarshipRegion
from enums import ScholarshipCategory, GradeCriterionType

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _log_prefix(scholarship: Scholarship) -> str:
    return f"ID {scholarship.original_id} ({scholarship.product_name})"


def validate_scholarship_data(
    scholarship: Scholarship,
    grade_criteria: List[GradeCriterion],
    income_criteria: List[IncomeCriterion],
    general_criteria: List[GeneralCriterion],
    scholarship_regions: List[ScholarshipRegion],
    id_to_region_map: Dict[int, Any]
) -> bool:
    validation_checks = [
        _validate_application_dates(scholarship),
        _validate_category_and_criteria_existence(scholarship, grade_criteria, income_criteria, general_criteria),
        _validate_recipient_numbers(scholarship),
        _validate_boolean_flag_consistency(scholarship),
        _validate_notes_extraction(scholarship),
        _validate_all_grade_criteria_fields(grade_criteria, scholarship),
        _validate_all_income_criteria_fields(income_criteria, scholarship),
        _validate_region_data(scholarship, scholarship_regions, id_to_region_map),
    ]

    if not all(validation_checks):
        #logger.error(f"{_log_prefix(scholarship)}: 최종 데이터 정합성 검증 실패.")
        return False

    #logger.info(f"{_log_prefix(scholarship)}: 최종 데이터 정합성 검증 통과.")
    return True


def _validate_application_dates(scholarship: Scholarship) -> bool:
    if scholarship.application_start_date > scholarship.application_end_date:
        logger.warning(f"{_log_prefix(scholarship)}: 모집 시작일({scholarship.application_start_date})이 "
                       f"종료일({scholarship.application_end_date})보다 늦습니다.")
        return False
    return True


def _validate_category_and_criteria_existence(
    scholarship: Scholarship,
    grade_criteria: List[GradeCriterion],
    income_criteria: List[IncomeCriterion],
    general_criteria: List[GeneralCriterion]
) -> bool:
    if (scholarship.scholarship_category == ScholarshipCategory.GRADE and 
        not grade_criteria and scholarship.grade_criteria_detail):
        logger.warning(f"{_log_prefix(scholarship)}: '성적우수' 장학금이지만, 성적 기준이 없습니다.")
        return False
    if (scholarship.scholarship_category == ScholarshipCategory.INCOME and 
        not income_criteria and not general_criteria and scholarship.income_criteria_detail):
        logger.warning(f"{_log_prefix(scholarship)}: '소득구분' 장학금이지만, 소득 기준이 없습니다.")
        return False
    return True


def _validate_recipient_numbers(scholarship: Scholarship) -> bool:
    total = scholarship.num_of_recipients_total
    categories = scholarship.recipients_by_category

    if total is not None and categories:
        text = scholarship.selection_personnel_detail or ""
        cat_sum = sum(categories.values())

        # 검증 통과 조건 (이 중 하나라도 만족하면 정상)
        # 1. 합계가 총계와 정확히 일치
        if total == cat_sum:
            return True
        
        # 2. '포함', '내외', '정도' 키워드가 있고, 합계가 총계보다 작거나 같음
        if any(k in text for k in ['포함', '내외', '정도']) and cat_sum <= total:
            return True
        
        # 위 조건들을 모두 만족하지 못하면 불일치 로그 기록
        logger.info(f"{_log_prefix(scholarship)}: 총 선발인원({total})과 "
                    f"구분별 인원 합계({cat_sum})가 불일치합니다.")
    return True


def _validate_boolean_flag_consistency(scholarship: Scholarship) -> bool:
    """
    is_duplicate_support_restricted 플래그 검증 시,
    단순히 '가능' 단어 존재 여부가 아닌, 파서가 놓쳤을 '명백한 전체 허용' 표현과의 모순만 체크하도록 변경
    """
    # ... 추천 플래그 관련 로직은 동일 ...
    if not scholarship.is_recommendation_required:
        if any(k in (scholarship.recommendation_needed_detail or '') for k in ["필요", "요함", "추천"]):
            logger.info(f"{_log_prefix(scholarship)}: 추천 플래그(False)와 텍스트 내용이 불일치할 수 있습니다.")

    # is_duplicate_support_restricted가 True(제한)로 설정된 경우
    if scholarship.is_duplicate_support_restricted:
        detail = scholarship.qualification_restriction_detail or ''

        # 'A는 안되지만 B는 가능'과 같은 복합 문장을 제외하고,
        # 문장 전체가 '중복 수혜가 가능하다'는 뉘앙스를 가지는, 모호하지 않은 패턴 목록
        # 이 패턴이 발견되면, 파서가 True로 설정한 것이 오류일 가능성이 높다고 판단할 수 있음.
        unambiguous_permission_patterns = [
            r'^(?!.*(불가|제외|금지|없음|안됨)).*중복\s*(수혜|지원)[이가]?\s*가능', # 부정어 없이 '중복가능'으로 끝나는 문장
            r'^(?!.*(불가|제외|금지|없음|안됨)).*등록금\s*범위\s*내', # 부정어 없이 '등록금 범위 내'만 있는 문장
        ]

        # 부정적인 단서(불가, 제외 등)가 전혀 없이, 명백한 허용 표현만 존재할 때 경고
        if any(re.search(pattern, detail) for pattern in unambiguous_permission_patterns):
            logger.info(f"{_log_prefix(scholarship)}: 중복 수혜 제한 플래그(True)와 텍스트 내용이 불일치할 수 있습니다.")

    return True


def _validate_notes_extraction(scholarship: Scholarship) -> bool:
    detail_fields_to_check = [
        ("grade_criteria_detail", scholarship.grade_criteria_detail),
        ("income_criteria_detail", scholarship.income_criteria_detail),
        ("support_detail", scholarship.support_detail),
        ("specific_qualification_detail", scholarship.specific_qualification_detail),
        ("region_residence_detail", scholarship.region_residence_detail),
        ("selection_method_detail", scholarship.selection_method_detail),
        ("selection_personnel_detail", scholarship.selection_personnel_detail),
        ("qualification_restriction_detail", scholarship.qualification_restriction_detail),
        ("recommendation_needed_detail", scholarship.recommendation_needed_detail),
        ("required_documents_detail", scholarship.required_documents_detail),
    ]
    for field_name, detail_text in detail_fields_to_check:
        if detail_text and '※' in detail_text and not detail_text.strip().startswith('※'):
            logger.warning(f"{_log_prefix(scholarship)}: 전처리 후에도 '{field_name}' 필드에 '※'가 남아있습니다. "
                           f"Transformer의 비고 추출 로직을 확인하세요.")
            return False
    return True


def _validate_all_grade_criteria_fields(grade_criteria: List[GradeCriterion], scholarship: Scholarship) -> bool:
    for g in grade_criteria:
        if g.type == GradeCriterionType.CREDITS and g.credits is None:
            logger.warning(f"{_log_prefix(scholarship)}: CREDITS 기준이지만 credits가 없습니다.")
            return False
        if g.type == GradeCriterionType.GPA:
            if g.score3 is None and g.score5 is None:
                logger.warning(f"{_log_prefix(scholarship)}: GPA 기준이지만 score3/score5가 모두 없습니다.")
                return False
    return True


def _validate_all_income_criteria_fields(income_criteria: List[IncomeCriterion], scholarship: Scholarship) -> bool:
    for i in income_criteria:
        if i.scholarship_support_interval and not (1 <= i.scholarship_support_interval <= 10):
            logger.warning(f"{_log_prefix(scholarship)}: 학자금 지원구간({i.scholarship_support_interval})이 유효 범위를 벗어났습니다.")
            return False
        if i.income_percentile_band and not (1 <= i.income_percentile_band <= 10):
            logger.warning(f"{_log_prefix(scholarship)}: 소득분위({i.income_percentile_band}) 값이 유효하지 않습니다.")
            return False
        if i.median_income_ratio and not (0 <= i.median_income_ratio <= 500):
            logger.warning(f"{_log_prefix(scholarship)}: 중위소득 비율({i.median_income_ratio})이 비정상적입니다.")
            return False
    return True


def _validate_region_data(
    scholarship: Scholarship,
    scholarship_regions: List[ScholarshipRegion],
    id_to_region_map: Dict[int, Any]
) -> bool:
    """지역 정보의 정합성을 검증합니다."""
    # '지역연고' 장학금인데 지역 정보가 없는 경우
    if scholarship.scholarship_category == ScholarshipCategory.LOCAL and not scholarship_regions and scholarship.region_residence_detail:
        #logger.warning(f"{_log_prefix(scholarship)}: '지역연고' 장학금이지만, 텍스트에서 지역 정보를 추출하지 못했습니다.")
        return False

    # 자식 지역(시/군/구)은 있는데 부모 지역(시/도)이 없는 경우 (계층 구조 무결성)
    if scholarship_regions and id_to_region_map:
        region_ids_present = {sr.region_id for sr in scholarship_regions}
        for region_id in region_ids_present:
            region_info = id_to_region_map.get(region_id)
            # region_info가 있고, parent_id가 None이 아니면 자식 노드임
            if region_info and region_info.get('parent_id') is not None:
                if region_info['parent_id'] not in region_ids_present:
                    parent_name = id_to_region_map.get(region_info['parent_id'], {}).get('name', '알 수 없음')
                    logger.warning(f"{_log_prefix(scholarship)}: 지역 정보에 '{region_info['name']}'이(가) 있지만, "
                                   f"부모 지역인 '{parent_name}'이(가) 누락되었습니다.")
                    return False
    return True