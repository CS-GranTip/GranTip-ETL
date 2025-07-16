import re
from typing import Optional, List, Set, Dict
from models.criterion.income_criterion import IncomeCriterion
from models.criterion.general_criterion import GeneralCriterion
from enums import QualificationCode, AidType

# 키워드와 Enum 코드를 매핑
QUALIFICATION_KEYWORDS = {
    QualificationCode.LOW_INCOME: ['기초생활수급자', '수급자', '차상위', '저소득', '생계급여', '의료급여', '주거급여', '교육급여', '서민'],
    QualificationCode.MULTI_CHILD: ['다자녀'],
    QualificationCode.SINGLE_PARENT: ['한부모', '모·부자'],
    QualificationCode.BOY_GIRL_HEADED: ['소년소녀', '청소년 가장'],
    QualificationCode.DISABLED: ['장애인', '장애가정'],
    QualificationCode.MULTICULTURAL: ['다문화'],
    QualificationCode.NATIONAL_MERIT: ['국가유공자', '보훈', '의사상자'],
    QualificationCode.NORTH_KOREAN_SETTLER: ['북한이탈주민', '새터민'],
    QualificationCode.FRESHMAN: ['신입생', '입학생'],
    QualificationCode.ENROLLED: ['재학생']
}

PREFERENCE_KEYWORDS = ["우선", "가산점", "우대", "권고"]
LIVING_AID_KEYWORDS = ['생활비', '생활지원금']
TUITION_AID_KEYWORDS = ['학자금']

def _extract_qualifications(text: str) -> Set[QualificationCode]:
    """텍스트에서 자격 조건 키워드를 찾아 Enum Set으로 반환"""
    found_quals = set()
    for code, keywords in QUALIFICATION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                found_quals.add(code)
    return found_quals

def extract_income_criteria(scholarship_id: int, raw_text: Optional[str]) -> Dict[str, List]:
    """
    '소득기준 상세내용' 텍스트를 파싱하여 GeneralCriterion과 IncomeCriterion 객체 리스트를 반환
    """
    if not raw_text:
        return {"general_criteria": [], "income_criteria": []}
    
    general_req_quals = set()
    general_pref_quals = set()
    income_criteria: List[IncomeCriterion] = []
    
    # 원본 텍스트 전체의 '우대' 컨텍스트 결정
    is_preference_block = False
    if raw_text.strip().startswith('※'):
        header = raw_text.split('○', 1)[0]
        if any(keyword in header for keyword in PREFERENCE_KEYWORDS):
            is_preference_block = True

    # '○'를 기준으로 규칙들을 분리
    rules_text = [rule.strip() for rule in raw_text.split('○') if rule.strip()]
        
    priority_counter = 1
    
    for text in rules_text:
        # '※' 제거
        clean_text = text.lstrip('※').strip()
        if not clean_text:
            continue
        
        # 자격 조건 키워드 추출
        qualifications = _extract_qualifications(clean_text)

        # 최종 '우대' 여부 판단 : 블록 전체 또는 개별 규칙에 우대 키워드가 있는지 확인 
        is_local_preference = any(keyword in clean_text for keyword in PREFERENCE_KEYWORDS)
        is_final_preference = is_preference_block or is_local_preference

        # 지원금 종류(AidType) 판단
        current_aid_type = None
        if any(keyword in clean_text for keyword in LIVING_AID_KEYWORDS):
            current_aid_type = AidType.LIVING
        elif any(f"{keyword} :" in clean_text for keyword in TUITION_AID_KEYWORDS):
            current_aid_type = AidType.TUITION
    
        # --- [수정된 핵심 로직] ---
        
        # 정량적 기준 추출: 모든 검색 결과를 독립적인 `_match` 변수에 저장합니다.
        range_match = re.search(r'소득\s*분위\s*[\d-]+\s*~\s*(\d+)\s*구간', clean_text)
        interval_match = re.search(r'(\d+)\s*구간', clean_text)
        band_match = re.search(r'(\d+)\s*분위', clean_text)
        ratio_match = re.search(r'중위소득\s*(\d+)', clean_text)

        # '소득분위 X~Y 구간' 형태의 범위를 먼저 체크
        if range_match:
            band_match = range_match  # '소득분위'로 처리하기 위해 band_match를 덮어씁니다.
            interval_match = None     # '구간'은 중복 해석되므로 무시합니다.
        
        # 소득 무관 규칙 확인
        is_ignored = bool(re.search(r'소득\s*분위\s*무관|소득무관|소득\s*제한\s*없음', clean_text))

        
        # 소득/재산 관련 규칙 존재 여부 판단
        has_income_rule = any([interval_match, band_match, ratio_match])
        # 소득 무관은 무조건 IncomeCriterion으로 분기
        if is_ignored or has_income_rule:
            req_quals = sorted(list(qualifications)) if not is_final_preference else []
            pref_quals = sorted(list(qualifications)) if is_final_preference else []

            income_criterion = IncomeCriterion(
                scholarship_id=scholarship_id,
                priority=priority_counter,
                description=clean_text,
                aid_type=current_aid_type,
                required_qualifications=req_quals,
                preference_qualifications=pref_quals,
                ignore_income_and_assets=is_ignored,
                scholarship_support_interval=int(interval_match.group(1)) if interval_match else None,
                income_percentile_band=int(band_match.group(1)) if band_match else None,
                median_income_ratio=int(ratio_match.group(1)) if ratio_match else None,
            )
            income_criteria.append(income_criterion)
            priority_counter += 1
        elif qualifications:
            if is_final_preference:
                general_pref_quals.update(qualifications)
            else:
                general_req_quals.update(qualifications)

    # 최종적으로 GeneralCriterion 객체 1개 생성
    general_criterion_list = []
    if general_req_quals or general_pref_quals:
        general_criterion_list.append(GeneralCriterion(
            scholarship_id=scholarship_id,
            required_qualifications=sorted(list(general_req_quals)),
            preference_qualifications=sorted(list(general_pref_quals))
        ))

    return {
        "general_criteria": general_criterion_list,
        "income_criteria": income_criteria
    }

if __name__ == "__main__":
    test_cases = [
        # --- 실제 데이터 기반 테스트 케이스 ---
        {"id": 1, "description": "조건부 소득 기준 (장애)", "raw_text": "○ 취약계층(장애가정) : 본인 또는 부양의무자가 장애인으로 부양의무자의 합산 월 소득이 기준 중위소득 70%(학자금지원구간 3구간이내)이하 장애가족 자녀"},
        {"id": 2, "description": "소득 무관 규칙", "raw_text": "○ 다자녀가정의 경우 소득분위 무관"},
        {"id": 3, "description": "일반 자격 조건만 존재", "raw_text": "○ 저소득 가정 기초생활수급자·법정차상위계층·한부모가족·장애인연금수급자"},
        {"id": 4, "description": "※ 우대 컨텍스트 블록", "raw_text": "※ 우선선정 권고사항○ 기초생활 수급자/차상위계층인 대학생○ 장애인 대학생○ 다자녀가구"},
        {"id": 5, "description": "순위/우선 혼합 규칙", "raw_text": "○ 1순위 : 기초생활수급지/차상위/한부모가족 우선 선발○ 2순위 : 2024 기준중위소득 100%이하"},
        {"id": 6, "description": "여러 줄 복합 규칙", "raw_text": "○ 신입생 기준중위소득 100%이하○ 재학생 한국장학재단 학자금 지원구간 5구간 이내"},
        {"id": 7, "description": "건강보험료/재산세 기준", "raw_text": "○ 건강보험료 지역 12만원/직장 7만원 이하인 해당학생\n○ 재산세 50만원 이하"},
    ]

    print("="*60)
    print("Income Parser 실제 데이터 기반 테스트를 시작합니다...")
    print("="*60)

    for case in test_cases:
        test_id, description, raw_text = case["id"], case["description"], case["raw_text"]
        print(f"\n--- [TEST CASE {test_id}: {description}] ---")
        print(f"INPUT: \"{raw_text}\"")
        
        result = extract_income_criteria(test_id, raw_text)
        
        print(" > General Criteria:")
        if result["general_criteria"]:
            for gc in result["general_criteria"]: print(f"   {gc.model_dump_json(indent=2)}")
        else:
            print("   (없음)")

        print(" > Income Criteria:")
        if result["income_criteria"]:
            for ic in result["income_criteria"]: print(f"   {ic.model_dump_json(indent=2)}")
        else:
            print("   (없음)")

    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60)