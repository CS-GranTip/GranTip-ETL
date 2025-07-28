import re
from typing import List
import sys
#models경로 불러오기
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from models.criterion.grade_criterion import GradeCriterion  # models.py에서 GradeCriterion 임포트
from enums import GradeCriterionType, BaseSemester, ThresholdDirection

# 원본 grade_parser.py의 extract_grade_criteria 함수
def extract_grade_criteria(scholarship_id: int, raw_text: str) -> List[GradeCriterion]:
    """
    성적기준 텍스트에서 성적만 추출하여 GradeCriterion 객체 리스트 반환.
    """
    if not raw_text:
        return []

    criteria = []    

    groups = re.split(r'○', raw_text)  # ○를 보고 분할
    
    for i, text in enumerate(groups):
        if not text.strip():
            continue

        criteria.append(GradeCriterion(
            scholarship_id=scholarship_id,
            group='그룹없음',
            type=GradeCriterionType.ETC.value,
            description=text
        ))

        # 그룹 설정
        group = "재학생"
        if "신입생" in text:
            group = "신입생"  
        elif "대학원" in text:
            group = "대학원생"
        criteria[-1].group = group

        # 기준 학기 설정
        semester = BaseSemester.AVG.value   # 기본 평균
        findSem = re.search(r'(직전|전)\s*\w*(학기|학년)', text)
        if findSem:
            if "두" in findSem.group() or "2" in findSem.group() or "학년" in findSem.group():
                semester = BaseSemester.LAST2.value     # 두개 학기
            else:
                semester = BaseSemester.LAST.value      # 한개 학기
        elif "1년" in text:
            semester = BaseSemester.LAST2.value     # 두개 학기
        elif "학기" in text:
            semester = BaseSemester.LAST.value      # 한개 학기
        criteria[-1].semester = semester

        # 성적 추출
        gpa_match = re.findall(r'\d\.\d+', text)  # 모든 n.n 형식의 평점 추출
        gpaABC_match = None
        if not gpa_match:
            gpaABC_match = re.search(r'([A-D])[+-]?', text)  # ABC 형식 패턴 수정 (A-D 뒤에 + 또는 - 옵션)

        if gpa_match:
            # 성적 정렬 후 4.5, 4.3이 아닌 것만 뽑아내서 매핑
            scores = sorted([float(j) for j in gpa_match if float(j) not in (4.5, 4.3)], reverse=True)
            score5 = scores[0] if scores else 0.0
            score3 = scores[1] if len(scores) > 1 else 0.0
            
            # 만약 4.3에 들어가야 할 게 잘못 들어갔을 경우 재매핑
            if score5 != 0.0 and score3 == 0.0 and len(gpa_match) > 1 and '4.3' in gpa_match:
                score3 = score5
                score5 = 0.0
            criteria[-1].type = GradeCriterionType.GPA.value             
            criteria[-1].score5 = float(score5)
            criteria[-1].score3 = float(score3)
            criteria[-1].direction = ThresholdDirection.ABOVE.value 
              
        elif gpaABC_match:
            criteria[-1].type = GradeCriterionType.GPA.value
            criteria[-1].direction = ThresholdDirection.ABOVE.value
            
            gpa_scores = {
                "A+": (4.5, 4.3),
                "A": (4.0, 4.0),
                "A-": (0.0, 3.7),
                "B+": (3.5, 3.3),
                "B": (3.0, 3.0),
                "B-": (0.0, 2.7),
                "C+": (2.5, 2.3),
                "C": (2.0, 2.0),
                "C-": (0.0, 1.7),  # 표준 GPA 기준 적용
                "D+": (1.5, 1.3),
                "D": (1.0, 1.0),
                "D-": (0.0, 0.7),
            }
            match_str = gpaABC_match.group(0)  # match 객체에서 문자열 추출
            score5, score3 = gpa_scores.get(match_str, (0.0, 0.0))
            criteria[-1].score5 = score5
            criteria[-1].score3 = score3

        # 이수학점 추출
        credits_match = re.search(r'(\d+)학점', text)
        if credits_match:
            # 학점 기준이 없을 경우 이수학점 기준으로 변경
            if criteria[-1].type == GradeCriterionType.ETC.value:
                criteria[-1].type = GradeCriterionType.CREDITS.value    
            criteria[-1].credits = int(credits_match.group(1))
            criteria[-1].direction = ThresholdDirection.ABOVE.value    
        
        # 등급/석차 예: '3등급 이상'
        rank_match = re.search(r'(\d)등급', text)
        if rank_match:
            criteria[-1].type = GradeCriterionType.RANK.value
            criteria[-1].rank = int(rank_match.group(1))  # 등급은 정수로 변환
            criteria[-1].unit = '등급'
            criteria[-1].direction = ThresholdDirection.BELOW.value
            criteria[-1].keyword = '등급'  
            # 수능등급인가? 
            test_check = re.search(r'수능|수학능력시험평가', text)
            if test_check:
                criteria[-1].keyword = '수능'
            # 내신등급인가?
            report_check = re.search(r'내신|고등학교|최종학력', text)
            if report_check:
                criteria[-1].keyword = '내신'
        
        # 키워드만 있는 경우 (예: '우수한 자')
        if not any([gpa_match, credits_match, rank_match]):
            criteria[-1].type = GradeCriterionType.ETC.value    
            criteria[-1].keyword = text.strip()
    return criteria