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
        _validate_category_and_criteria_existence(scholarship, grade_criteria, income_criteria),
        _validate_recipient_numbers(scholarship),
        _validate_boolean_flag_consistency(scholarship),
        _validate_notes_extraction(scholarship),
        _validate_all_grade_criteria_fields(grade_criteria, scholarship),
        _validate_all_income_criteria_fields(income_criteria, scholarship),
        _validate_region_data(scholarship, scholarship_regions, id_to_region_map),
    ]

    if not all(validation_checks):
        logger.error(f"{_log_prefix(scholarship)}: 최종 데이터 정합성 검증 실패.")
        return False

    logger.info(f"{_log_prefix(scholarship)}: 최종 데이터 정합성 검증 통과.")
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
    income_criteria: List[IncomeCriterion]
) -> bool:
    if scholarship.scholarship_category == ScholarshipCategory.GRADE and not grade_criteria:
        logger.warning(f"{_log_prefix(scholarship)}: '성적우수' 장학금이지만, 성적 기준이 없습니다.")
        return False
    if scholarship.scholarship_category == ScholarshipCategory.INCOME and not income_criteria:
        logger.warning(f"{_log_prefix(scholarship)}: '소득구분' 장학금이지만, 소득 기준이 없습니다.")
        return False
    return True


def _validate_recipient_numbers(scholarship: Scholarship) -> bool:
    if scholarship.num_of_recipients_total is not None and scholarship.recipients_by_category:
        total = sum(scholarship.recipients_by_category.values())
        if total != scholarship.num_of_recipients_total:
            logger.info(f"{_log_prefix(scholarship)}: 총 선발인원({scholarship.num_of_recipients_total})과 "
                        f"구분별 인원 합계({total})가 불일치합니다.")
    return True


def _validate_boolean_flag_consistency(scholarship: Scholarship) -> bool:
    if not scholarship.is_recommendation_required:
        if any(k in (scholarship.recommendation_needed_detail or '') for k in ["필요", "요함", "추천"]):
            logger.info(f"{_log_prefix(scholarship)}: 추천 플래그(False)와 텍스트 내용이 불일치할 수 있습니다.")
    if scholarship.is_duplicate_support_restricted:
        detail = scholarship.qualification_restriction_detail or ''
        # '가능' 또는 '허용'이라는 단어가 '불가능', '비허용' 등의 부정 문맥이 아닌 경우만 잡음
        if re.search(r'(?<!불)가능', detail) or re.search(r'(?<!비)허용', detail):
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
    if scholarship.scholarship_category == ScholarshipCategory.LOCAL and not scholarship_regions:
        # 텍스트 자체가 없는 경우는 정상일 수 있으므로 경고하지 않음
        if scholarship.region_residence_detail:
            logger.warning(f"{_log_prefix(scholarship)}: '지역연고' 장학금이지만, 텍스트에서 지역 정보를 추출하지 못했습니다.")
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