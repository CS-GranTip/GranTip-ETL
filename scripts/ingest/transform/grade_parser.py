import re
from typing import List
import sys
#models경로 불러오기
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from models.criterion.grade_criterion import GradeCriterion  # models.py에서 GradeCriterion 임포트

# 원본 grade_parser.py의 extract_grade_criteria 함수
def extract_grade_criteria(scholarship_id: int, raw_text: str) -> List[GradeCriterion]:
    """
    성적기준 텍스트에서 성적만 추출하여 GradeCriterion 객체 리스트 반환.
    """
    criteria = []    
    # '해당없음' 전체 체크 (루프 밖으로 이동)
    if raw_text.strip() == '해당없음':
        criteria.append(GradeCriterion(
            scholarship_id=scholarship_id,
            group='그룹없음',
            type=GradeCriterionType.ETC,
            keyword='해당없음',
            description=raw_text
        ))
        return criteria
    groups = re.split(r'○', raw_text)  # o를 보고 분할
    
    for i, text in enumerate(groups):
        if not text.strip():
            continue

        criteria.append(GradeCriterion(
            scholarship_id=scholarship_id,
            group='그룹없음',
            type=GradeCriterionType.ETC.value,
            description=text
        ))

        #그룹설정
        group = "재학생"
        if "신입생" in text:
            group = "신입생"  
        elif "대학원" in text:
            group = "대학원생"
        criteria[-1].group = group

        #기준 학기 설정
        semester = BaseSemester.AVG.value   #기본 평균
        findSem  = re.search(r'(직전|전)\s*\w*(학기|학년)', text)
        if findSem:
            if("두" in findSem.group() or "2" in findSem.group() or "학년" in findSem.group()):
                semester = BaseSemester.LAST2.value     #두개학기
            else:
                semester = BaseSemester.LAST.value      #한개학기
        elif "1년" in text:
            semester = BaseSemester.LAST2.value     #두개학기
        elif "학기" in text:
            semester = BaseSemester.LAST.value      #한개학기
        criteria[-1].semester = semester

        #성적 추출
        gpa_match = re.findall(r'\d\.\d+', text) #모든 n.n의 형식을 가지는 평점 형식을 불러옴
        if not gpa_match:
            gpaABC_match = re.search(r'A|B|C|D(\+*)(\-*)',text) ##혹은 ABC형식으로 된 것 찾기

        if gpa_match:
            score3 = 0.0
            score5 = 0.0
            for j in gpa_match:    
                if (float(j) != 4.5) & (float(j) != 4.3):     #형식중 4.5와 4.3등 기준값은 제거
                    if score5 == 0.0:      #더 큰값을 4.5에 넣고 작은 값은 4.3에 넣어줌.
                        score5 = float(j)
                    else:
                        if score5 < float(j):
                            score3 = score5
                            score5 = float(j)
                        else:
                            score3 = float(j)                     
            criteria[-1].type=GradeCriterionType.GPA.value             
            criteria[-1].score5=float(score5)
            criteria[-1].score3=float(score3)
            criteria[-1].direction=ThresholdDirection.ABOVE.value   
        elif gpaABC_match: 
            criteria[-1].type=GradeCriterionType.GPA.value 
            criteria[-1].direction=ThresholdDirection.ABOVE.value 
            if gpaABC_match == "A+":
                score5 = 4.5
                score3 = 4.3
            elif gpaABC_match == "A":
                score5 = 4.0
                score3 = 4.0
            elif gpaABC_match == "A-":
                score3 = 3.7
            elif gpaABC_match == "B+":
                score5 = 3.5
                score3 = 3.3
            elif gpaABC_match == "B":
                score5 = 3.0
                score3 = 3.0
            elif gpaABC_match == "B-":
                score3 = 2.7
            elif gpaABC_match == "C+":
                score5 = 2.5
                score3 = 2.3
            elif gpaABC_match == "C":
                score5 = 2.0
                score3 = 2.0
            elif gpaABC_match == "C-":
                score3 = 2.7
            elif gpaABC_match == "D+":
                score5 = 1.5
                score3 = 1.3
            elif gpaABC_match == "D":
                score5 = 1.0
                score3 = 1.0
            elif gpaABC_match == "D-":
                score3 = 0.7
            else:
                score5 = 0.0  # F 또는 기타
                score3 = 0.0  # F 또는 기타

        #이수학점 추출
        credits_match = re.search(r'(\d+)학점', text)
        if credits_match:
            #학점 기준이 없을 경우 이수학점 기준으로 변경
            if(criteria[-1].type == GradeCriterionType.ETC):
                criteria[-1].type=GradeCriterionType.CREDITS.value    
            criteria[-1].credits=int(credits_match.group(1))
            criteria[-1].direction=ThresholdDirection.ABOVE.value    
        
        # 등급/석차 예: '3등급 이상'
        rank_match = re.search(r'(\d)등급', text)
        if rank_match:
            criteria[-1].type=GradeCriterionType.RANK.value
            criteria[-1].rank=float(rank_match.group(1))
            criteria[-1].unit='등급'
            criteria[-1].direction=ThresholdDirection.ABOVE.value
            criteria[-1].keyword = '등급'  
            #수능등급인가? 
            test_check = re.search(r'수능'or'수학능력시험평가', text)
            if(test_check):
                criteria[-1].keyword = '수능'
            #내신등급인가?
            report_check = re.search(r'내신'or'고등학교'or'최종학력', text)
            if(report_check):
                criteria[-1].keyword = '내신'
        
        # 키워드만 있는 경우 (예: '우수한 자')
        if not any([gpa_match, credits_match, rank_match]):
            criteria[-1].type=GradeCriterionType.ETC.value    
            criteria[-1].keyword=text.strip()
    return criteria