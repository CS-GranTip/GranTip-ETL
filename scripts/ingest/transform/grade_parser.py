import re
from typing import List
#models경로 불러오기
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from models.criterion.grade_criterion import GradeCriterion  # models.py에서 GradeCriterion 임포트

def extract_grade_criteria(scholarship_id: int, raw_text: str) -> List[GradeCriterion]:
    """
    성적기준 텍스트에서 성적만 추출하여 GradeCriterion 객체 리스트 반환.
    """
    criteria = []
    
    # 텍스트가 '해당없음'이면 ETC 타입으로 처리
    if raw_text.strip() == '해당없음':
        criteria.append(GradeCriterion(
            scholarship_id=scholarship_id,
            group='전체',
            type=GradeCriterionType.ETC,
            keyword='해당없음',
            description=raw_text
        ))
        return criteria
    
    # 그룹 분해 (예: (신입생) ... ○ (재학생) ...)
    groups = re.split(r'\(신입생\)|○ \(재학생\)', raw_text)  # 그룹 키워드로 분할
    group_names = ['전체'] if len(groups) == 1 else ['신입생', '재학생']  # 동적 그룹 할당
    
    for i, text in enumerate(groups):
        if not text.strip():
            continue
        group = group_names[i] if i < len(group_names) else '기타'
        
        # Regex로 성적 추출
        # GPA 예: '평균 2.75 이상 (4.3만점은 2.6이상)'
        gpa_match = re.search(r'성적 평균 (\d+\.?\d*) 이상.*\((\d+\.?\d*)만점은 (\d+\.?\d*)이상\)', text)
        if gpa_match:
            criteria.append(GradeCriterion(
                scholarship_id=scholarship_id,
                group=group,
                type=GradeCriterionType.GPA,
                score=float(gpa_match.group(1)),
                max_score=float(gpa_match.group(2)),
                direction=ThresholdDirection.ABOVE,
                description=text
            ))
        
        # 학점 예: '12학점 이상'
        credits_match = re.search(r'(\d+)학점 이상', text)
        if credits_match:
            criteria.append(GradeCriterion(
                scholarship_id=scholarship_id,
                group=group,
                type=GradeCriterionType.CREDITS,
                credits=int(credits_match.group(1)),
                direction=ThresholdDirection.ABOVE,
                description=text
            ))
        
        # 등급/석차 예: '3등급 이상'
        rank_match = re.search(r'(\d+)등급 이상', text)
        if rank_match:
            criteria.append(GradeCriterion(
                scholarship_id=scholarship_id,
                group=group,
                type=GradeCriterionType.RANK,
                rank=float(rank_match.group(1)),
                unit='등급',
                direction=ThresholdDirection.ABOVE,
                description=text
            ))
        
        # 키워드만 있는 경우 (예: '우수한 자')
        if not any([gpa_match, credits_match, rank_match]):
            criteria.append(GradeCriterion(
                scholarship_id=scholarship_id,
                group=group,
                type=GradeCriterionType.ETC,
                keyword=text.strip(),
                description=text
            ))
    
    return criteria