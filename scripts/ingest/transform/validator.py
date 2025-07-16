import re
import logging
from typing import List
from models.scholarship import Scholarship
from models.criterion.grade_criterion import GradeCriterion
from models.criterion.income_criterion import IncomeCriterion
from models.criterion.general_criterion import GeneralCriterion
from enums import ScholarshipCategory, GradeCriterionType

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _log_prefix(scholarship: Scholarship) -> str:
    return f"ID {scholarship.id} ({scholarship.product_name})"


def validate_scholarship_data(
    scholarship: Scholarship,
    grade_criteria: List[GradeCriterion],
    income_criteria: List[IncomeCriterion],
    general_criteria: List[GeneralCriterion]
) -> bool:
    validation_checks = [
        _validate_application_dates(scholarship),
        _validate_category_and_criteria_existence(scholarship, grade_criteria, income_criteria),
        _validate_recipient_numbers(scholarship),
        _validate_boolean_flag_consistency(scholarship),
        _validate_notes_extraction(scholarship),
        _validate_all_grade_criteria_fields(grade_criteria, scholarship),
        _validate_all_income_criteria_fields(income_criteria, scholarship),
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
