from enum import Enum

class ProviderType(str, Enum):
    LOCAL_GOV = "LOCAL_GOV"
    PUBLIC_ORG = "PUBLIC_ORG"
    ETC = "ETC"

class ProductType(str, Enum):
    SCHOLARSHIP = "SCHOLARSHIP"
    LOAN = "LOAN"

class ScholarshipCategory(str, Enum):
    LOCAL = "LOCAL"
    SPECIALTY = "SPECIALTY"
    GRADE = "GRADE"
    INCOME = "INCOME"
    DISABILITY = "DISABILITY"
    ETC = "ETC"

# --- 성적 기준 관련 Enum ---

# 성적 기준의 종류
class GradeCriterionType(str, Enum):
    GPA = "GPA"
    PERCENTILE = "PERCENTILE"
    RANK = "RANK"
    CREDITS = "CREDITS"
    QUALITATIVE = "QUALITATIVE"
    ETC = "ETC"

# 기준의 방향 (이상, 이하, 이내 등)
class ThresholdDirection(str, Enum):
    ABOVE = "ABOVE"    
    BELOW = "BELOW"
    WITHIN = "WITHIN"
    NONE = "NONE"

#기준 학기
class BaseSemester(str, Enum):
    LAST = "LAST"
    LAST2 = "LAST2"
    AVG = "AVG"
    NONE = "NONE"

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