from enum import Enum

class ProviderType(str, Enum):
    LOCAL_GOV = "지자체(출자출연기관)"
    PUBLIC_ORG = "공공기관"
    ETC = "기타"

class ProductType(str, Enum):
    SCHOLARSHIP = "장학금"
    LOAN = "학자금"

class ScholarshipCategory(str, Enum):
    LOCAL = "지역연고"
    SPECIALTY = "특기자"
    GRADE = "성적우수"
    INCOME = "소득구분"
    DISABILITY = "장애인"
    ETC = "기타"

# --- 성적 기준 관련 Enum ---

# 성적 기준의 종류
class GradeCriterionType(str, Enum):
    GPA = "평점"
    PERCENTILE = "백분위"
    RANK = "석차/등급"
    CREDITS = "이수학점"
    QUALITATIVE = "정성평가"
    ETC = "기타"

# 기준의 방향 (이상, 이하, 이내 등)
class ThresholdDirection(str, Enum):
    ABOVE = "이상"    
    BELOW = "이하"
    WITHIN = "이내"
    NONE = "해당없음"

#기준 학기
class BaseSemester(str, Enum):
    LAST = "직전학기"
    LAST2 = "직전두개학기"
    AVG = "전체학기"
    NONE = "해당없음"

class QualificationCode(str, Enum):
    """
    실제 장학금 데이터의 소득 기준 조건과 직접 연결되고,
    사용자 정보와 매칭 가능한 자격 코드
    """

    # --- 사회/경제적 상태 (Socio-Economic Status) ---
    LOW_INCOME = "LOW_INCOME"            # 저소득층 (기초/차상위 포함)

    # --- 가구/개인 특성 (Household & Personal Attributes) ---
    MULTI_CHILD = "MULTI_CHILD"          # 다자녀 가구
    SINGLE_PARENT = "SINGLE_PARENT"      # 한부모가족
    BOY_GIRL_HEADED = "BOY_GIRL_HEADED"  # 소년소녀가장 (orphan 필드와 연결)
    DISABLED = "DISABLED"                # 장애인 (본인 또는 가구원)
    MULTICULTURAL = "MULTICULTURAL"      # 다문화가정
    NATIONAL_MERIT = "NATIONAL_MERIT"    # 국가유공자 / 보훈대상자
    NORTH_KOREAN_SETTLER = "NORTH_KOREAN_SETTLER" # 북한이탈주민

    # --- 학적 상태 (Academic Status) ---
    FRESHMAN = "FRESHMAN"                # 신입생 / 입학생
    ENROLLED = "ENROLLED"                # 재학생

class AidType(str, Enum):
    TUITION = "TUITION"  # 학자금
    LIVING = "LIVING"    # 생활비