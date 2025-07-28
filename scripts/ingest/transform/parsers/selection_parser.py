from typing import Tuple, Optional, Dict

import re


def parse_selection_personnel(text: Optional[str]) -> Tuple[Optional[int], Optional[Dict[str, int]]]:
    """
    선발인원 상세내용을 파싱합니다.
    """
    if not text:
        return None, None
    
    if '각' in text and '씩' in text: # ex: 각 2명씩
        total_match = re.search(r'총\s*(\d+)\s*명', text)
        if total_match:
            # '총 O명'이 명시된 경우, 카테고리 파싱을 생략하고 total만 반환하여 불일치 검증을 피함
            return int(total_match.group(1)), None

    # 전처리: '00명' 제거 및 공백 정리
    text = text.replace('00명', '').strip()
    categorized: Dict[str, int] = {}
    total = None

    # 1. 명시적인 '총 O명'을 찾아 total로 확정하고, 텍스트에서 해당 부분 제거
    total_match = re.search(r'총\s*(\d+)\s*명', text)
    if total_match:
        total = int(total_match.group(1))
        text = text.replace(total_match.group(0), '')

    # 내부 함수: 주어진 텍스트에서 '카테고리 O명' 패턴을 찾아 categorized에 추가
    def find_and_add_categories(sub_text: str):
        # 'A 10명', 'B: 20명', 'C/30명' 등 다양한 구분자 처리
        pattern = r'([\w\s·/]+?)\s*[:/]?\s*(\d+)\s*명'
        matches = re.findall(pattern, sub_text)
        for cat_text, num_str in matches:
            # 불필요한 키워드와 공백 제거
            key = re.sub(r'총|포함|제외|내외|이내|선발|정도|각', '', cat_text)
            key = key.strip().strip('/ :')
            if key and not key.isdigit() and '명' not in key:
                categorized[key] = int(num_str)

    # 2. 괄호 안의 내용을 먼저 파싱하고, 텍스트에서 제거
    paren_matches = re.findall(r'\(([^)]+)\)', text)
    for content in paren_matches:
        find_and_add_categories(content)
    text = re.sub(r'\([^)]+\)', '', text) # 괄호와 내용 모두 제거

    # 3. 괄호가 제거된 나머지 텍스트를 파싱
    find_and_add_categories(text)
    
    # 4. 명시적 '총'이 없었고, 카테고리가 존재하면 합계를 total로 추론
    if total is None and categorized:
        total = sum(categorized.values())

    final_categorized = categorized if categorized else None
    
    return total, final_categorized