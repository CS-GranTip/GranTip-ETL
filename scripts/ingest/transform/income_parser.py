from typing import Optional, List
from models.criterion.grade_criterion import GradeCriterion 

def extract_income_criteria(text: Optional[str], scholarship_id: int) -> List[GradeCriterion]:
    """
    '성적기준 상세내용' 텍스트를 파싱하여 GradeCriterion 리스트를 반환합니다.
    """
    if not text:
        return []

    # TODO: 실제 정규표현식 및 규칙 기반 파싱 로직 구현
    return []