import logging
from typing import List
from models import Scholarship, GradeCriterion, IncomeCriterion
from enums import ScholarshipCategory, GradeCriterionType

# 로거 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- 메인 검증 함수 ---

def validate_scholarship_data(
    scholarship: Scholarship,
    grade_criteria: List[GradeCriterion],
    income_criteria: List[IncomeCriterion]
) -> bool:
    """
    하나의 장학금 데이터와 관련된 모든 정합성을 검증하는 메인 함수
    모든 검증을 통과해야 True를 반환
    """
    # 각 검증 함수를 리스트에 담아 순차적으로 실행
    validation_checks = [
        _validate_application_dates(scholarship),
        _validate_category_and_criteria_existence(scholarship, grade_criteria, income_criteria),
        _validate_recipient_numbers(scholarship),
        _validate_boolean_flag_consistency(scholarship),
        _validate_notes_extraction(scholarship),
        _validate_all_grade_criteria_fields(grade_criteria, scholarship.id),
        _validate_all_income_criteria_fields(income_criteria, scholarship.id)
    ]

    # 하나라도 False가 있으면 최종 결과를 False로 처리
    if not all(validation_checks):
        logger.error(f"ID {scholarship.id} ({scholarship.product_name}): 최종 데이터 정합성 검증 실패.")
        return False

    logger.info(f"ID {scholarship.id} ({scholarship.product_name}): 최종 데이터 정합성 검증 통과.")
    return True


# --- 세부 검증 헬퍼 함수들 ---

def _validate_application_dates(scholarship: Scholarship) -> bool:
    """모집 시작일이 종료일보다 늦지 않은지 검증합니다."""
    if scholarship.application_start_date > scholarship.application_end_date:
        logger.warning(
            f"ID {scholarship.id}: 모집 시작일({scholarship.application_start_date})이 "
            f"종료일({scholarship.application_end_date})보다 늦습니다."
        )
        return False
    return True


def _validate_category_and_criteria_existence(
    scholarship: Scholarship,
    grade_criteria: List[GradeCriterion],
    income_criteria: List[IncomeCriterion]
) -> bool:
    """장학금 유형에 맞는 핵심 기준 데이터가 존재하는지 검증합니다."""
    if scholarship.scholarship_category == ScholarshipCategory.GRADE and not grade_criteria:
        logger.warning(f"ID {scholarship.id}: '성적우수' 장학금이지만, 파싱된 성적 기준이 없습니다.")
        return False
    if scholarship.scholarship_category == ScholarshipCategory.INCOME and not income_criteria:
        logger.warning(f"ID {scholarship.id}: '소득구분' 장학금이지만, 파싱된 소득 기준이 없습니다.")
        return False
    return True


def _validate_recipient_numbers(scholarship: Scholarship) -> bool:
    """총 선발인원과 구분별 선발인원의 합계가 일치하는지 검증합니다."""
    if scholarship.num_of_recipients_total is not None and scholarship.recipients_by_category:
        sum_of_categorized = sum(scholarship.recipients_by_category.values())
        if scholarship.num_of_recipients_total != sum_of_categorized:
            logger.info(
                f"ID {scholarship.id}: 총 선발인원({scholarship.num_of_recipients_total})과 "
                f"구분별 인원 합계({sum_of_categorized})가 불일치합니다."
            )
            # 심각한 오류는 아니므로 True를 반환하고 로그만 남김
    return True


def _validate_boolean_flag_consistency(scholarship: Scholarship) -> bool:
    """요약된 Boolean 플래그와 원본 텍스트 내용의 일관성을 검증합니다."""
    # 추천서 필요 여부 검증
    if not scholarship.is_recommendation_required:
        text = scholarship.recommendation_needed_detail or ""
        if any(keyword in text for keyword in ["필요", "요함", "추천서", "추천"]):
            logger.info(f"ID {scholarship.id}: 추천 불필요(False) 플래그와 원본 텍스트 내용이 불일치할 수 있습니다.")

    # 중복수혜 제한 여부 검증
    if scholarship.is_duplicate_support_restricted:
        text = scholarship.qualification_restriction_detail or ""
        if any(keyword in text for keyword in ["가능", "허용", "무관"]):
            logger.info(f"ID {scholarship.id}: 중복수혜 제한(True) 플래그와 원본 텍스트 내용이 불일치할 수 있습니다.")
    return True


def _validate_notes_extraction(scholarship: Scholarship) -> bool:
    """
    '※' 비고가 원본 상세 내용 필드에서 성공적으로 제거되었는지 검증합니다.
    (전처리 로직의 성공 여부를 확인)
    """
    # 상세 내용 필드들
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
        if detail_text and "※" in detail_text:
            logging.warning(
                f"ID {scholarship.id}: 전처리 후에도 '{field_name}' 필드에 '※'가 남아있습니다. "
                f"Transformer의 비고 추출 로직을 확인하세요."
            )
            return False  # 전처리 실패로 간주

    return True


def _validate_all_grade_criteria_fields(grade_criteria: List[GradeCriterion], s_id: int) -> bool:
    """리스트에 포함된 모든 GradeCriterion 객체의 필드 유효성을 검증합니다."""
    for criterion in grade_criteria:
        # 타입별 필수 필드 존재 여부 검사
        if criterion.type == GradeCriterionType.GPA and (criterion.score is None or criterion.max_score is None):
            logger.warning(f"ID {s_id}: GPA 기준에 score 또는 max_score 필드가 누락되었습니다.")
            return False
        if criterion.type == GradeCriterionType.CREDITS and criterion.credits is None:
            logger.warning(f"ID {s_id}: 이수학점 기준에 credits 필드가 누락되었습니다.")
            return False
        # 값의 범위 검사
        if criterion.max_score and criterion.max_score not in [4.0, 4.3, 4.5, 100.0]:
            logger.info(f"ID {s_id}: GPA 만점 기준({criterion.max_score})이 일반적이지 않은 값입니다.")
    return True


def _validate_all_income_criteria_fields(income_criteria: List[IncomeCriterion], s_id: int) -> bool:
    """리스트에 포함된 모든 IncomeCriterion 객체의 필드 유효성을 검증합니다."""
    for criterion in income_criteria:
        # 값의 범위 검사
        if criterion.scholarship_support_interval and not (1 <= criterion.scholarship_support_interval <= 10):
            logger.warning(f"ID {s_id}: 학자금 지원구간({criterion.scholarship_support_interval})이 1~10 범위를 벗어났습니다.")
            return False
        if criterion.income_percentile_band and not (1 <= criterion.income_percentile_band <= 10):
            logger.warning(f"ID {s_id}: 소득분위({criterion.income_percentile_band})가 1~10 범위를 벗어났습니다.")
            return False
        if criterion.median_income_ratio and not (0 <= criterion.median_income_ratio <= 500):
            logger.warning(f"ID {s_id}: 중위소득 비율({criterion.median_income_ratio})이 비정상적인 값입니다.")
            return False
    return True



# --- 단위 테스트 및 실제 데이터 검증을 위한 실행 블록 ---

if __name__ == "__main__":
    import sys
    import os