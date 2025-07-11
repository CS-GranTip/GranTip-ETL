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
    NONE = "해당없음"

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