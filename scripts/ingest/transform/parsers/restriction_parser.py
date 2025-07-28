from typing import Optional

import re

def check_duplicate_support_restriction(text: Optional[str]) -> bool:
    """
    긍정/부정 패턴을 모두 탐색하고 가중치를 부여하여 최종 판단.
    '금지' 패턴이 하나라도 존재하면 '제한(True)'으로 판단하는 것을 우선한다.
    """
    if not text:
        return False

    # 허용을 의미하는 패턴 목록
    permission_patterns = [
        r'중복\s*(수혜|지원)[이가]?\s*가능',
        r'등록금\s*범위\s*내',
        r'차액만\s*지급',
    ]

    # 금지를 의미하는 패턴 목록
    prohibition_patterns = [
        r'중복\s*(수혜|지원|선발|지급|신청)\s*불가',
        r'중복\s*(수혜|지원)\s*금지',
        r'이중\s*(수혜|지원)\s*금지',
        r'(수혜|지원|선발)자\s*제외',
        r'1세대\s*1명만',
        r'한\s*종류만\s*수혜',
        # '가능'이 포함되지만 실제로는 금지인 경우
        r'가능하나\s*[^.]*?(불가|없음|제한|안됨)',
    ]

    # 텍스트에서 각 패턴의 발견 여부 확인
    is_permission_found = any(re.search(pattern, text) for pattern in permission_patterns)
    is_prohibition_found = any(re.search(pattern, text) for pattern in prohibition_patterns)

    # --- 최종 판단 로직 ---
    # 1. 금지 패턴이 하나라도 발견되면, 일부 허용 조항이 있더라도 '제한'으로 간주 (True)
    if is_prohibition_found:
        return True

    # 2. 금지 패턴은 없지만, 명백한 허용 패턴이 발견되면 '허용' (False)
    if is_permission_found:
        return False

    # 3. 명확한 허용/금지 패턴은 없지만, 일반적인 제한 키워드가 있다면 '제한'으로 간주 (True)
    general_restriction_keywords = [
        '타 장학금', '타장학금', '다른 장학금', '기수혜자', '이중지원'
    ]
    if any(keyword in text for keyword in general_restriction_keywords):
        return True

    # 4. 위의 모든 경우에 해당하지 않으면 제한 없음 (False)
    return False