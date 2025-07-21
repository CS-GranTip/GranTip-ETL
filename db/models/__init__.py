# db/models/__init__.py
from .region import Region
from .scholarship import Scholarship
from .scholarship_region import ScholarshipRegion
# 별칭으로 최소 import만 유지, 순환 방지
from .criterion.grade_criterion import GradeCriterion as GradeCriterionDBModel
from .criterion.income_criterion import IncomeCriterion as IncomeCriterionDBModel
from .criterion.general_criterion import GeneralCriterion as GeneralCriterionDBModel

__all__ = [
    "Region",
    "Scholarship",
    "ScholarshipRegion",
    "GradeCriterionDBModel",
    "IncomeCriterionDBModel",
    "GeneralCriterionDBModel"
]