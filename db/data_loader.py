# db/data_loader.py (보완된 버전)
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))  # 프로젝트 루트 (GranTip-ETL) 추가

from typing import List, Dict
from sqlalchemy.exc import IntegrityError
from db.database import SessionLocal
from db.models.scholarship import Scholarship as ScholarshipDBModel
from db.models.criterion.grade_criterion import GradeCriterion as GradeCriterionDBModel
from db.models.criterion.income_criterion import IncomeCriterion as IncomeCriterionDBModel
from db.models.criterion.general_criterion import GeneralCriterion as GeneralCriterionDBModel
from db.models.scholarship_region import ScholarshipRegion as ScholarshipRegionDBModel
from db.models.region import Region  # Region 모델 추가 (유효성 검증용)
from models.scholarship import Scholarship
from models.criterion.grade_criterion import GradeCriterion
from models.criterion.income_criterion import IncomeCriterion
from models.criterion.general_criterion import GeneralCriterion
from models.scholarship_region import ScholarshipRegion
import json

def load_to_db(valid_data: Dict[str, List]):
    """
    변환된 데이터를 받아 DB에 저장(UPSERT)합니다.
    지역 ID 유효성 검증과 다중 레코드 처리를 보완했습니다.
    """
    db = SessionLocal()
    try:
        # Region ID 매핑 로드 (이름 기반 매핑이 아닌 ID 유효성 체크용)
        region_ids = {r.id for r in db.query(Region.id).all()}  # 모든 region_id 집합
        print(f"Region 테이블에 {len(region_ids)}개의 ID가 존재합니다.")

        id_map = {}  # original_id -> db_id 매핑
        for s in valid_data["scholarships"]:
            s_dict = s.model_dump(exclude_unset=True)
            try:
                s_dict["university_category"] = json.dumps(s_dict.get("university_category", []))
                s_dict["grade_category"] = json.dumps(s_dict.get("grade_category", []))
                s_dict["department_category"] = json.dumps(s_dict.get("department_category", []))
                s_dict["recipients_by_category"] = json.dumps(s_dict.get("recipients_by_category", {}))
                s_dict["qualification_tags"] = json.dumps(s_dict.get("qualification_tags", []))
            except (TypeError, ValueError) as e:
                print(f"JSON 변환 오류 (Scholarship {s.original_id}): {e}")
                continue  # 오류 시 스킵

            db_s = db.query(ScholarshipDBModel).filter(ScholarshipDBModel.original_id == s.original_id).first()
            if db_s:
                for key, value in s_dict.items():
                    setattr(db_s, key, value)
                db_id = db_s.id
            else:
                db_s = ScholarshipDBModel(**s_dict)
                db.add(db_s)
                db.flush()
                db_id = db_s.id
            id_map[s.original_id] = db_id

        # Criteria 처리: 각 유형별로 기존 레코드 삭제 후 재삽입 (다중 레코드 지원)
        for key, model_class, pydantic_model in [
            ("grades", GradeCriterionDBModel, GradeCriterion),
            ("incomes", IncomeCriterionDBModel, IncomeCriterion),
            ("generals", GeneralCriterionDBModel, GeneralCriterion),
            ("regions", ScholarshipRegionDBModel, ScholarshipRegion)
        ]:
            items_to_add = []
            for item in valid_data[key]:
                item_dict = item.model_dump(exclude_unset=True)
                if key in ["grades", "incomes", "generals"]:
                    try:
                        item_dict["required_qualifications"] = json.dumps(item_dict.get("required_qualifications", []))
                        item_dict["preference_qualifications"] = json.dumps(item_dict.get("preference_qualifications", []))
                    except (TypeError, ValueError) as e:
                        print(f"JSON 변환 오류 ({key} for scholarship_id {item.scholarship_id}): {e}")
                        continue

                item_dict["scholarship_id"] = id_map.get(item.scholarship_id)
                if item_dict["scholarship_id"] is None:
                    print(f"유효하지 않은 scholarship_id: {item.scholarship_id}")
                    continue

                # Region 특수 처리: region_id 유효성 검증
                if key == "regions":
                    region_id = item_dict.get("region_id")
                    if region_id not in region_ids:
                        print(f"유효하지 않은 region_id {region_id} (scholarship_id {item_dict['scholarship_id']}) - 스킵")
                        continue

                items_to_add.append(model_class(**item_dict))

            # 기존 레코드 삭제 (scholarship_id별로)
            scholarship_ids = list(id_map.values())
            if scholarship_ids:
                db.query(model_class).filter(model_class.scholarship_id.in_(scholarship_ids)).delete(synchronize_session=False)
                db.commit()  # 삭제 커밋 (배치 처리 위해)

            # 새 레코드 추가
            if items_to_add:
                db.add_all(items_to_add)

        db.commit()
        print("DB 적재 완료.")
    except IntegrityError as e:
        db.rollback()
        print(f"DB 적재 오류 (무결성 위반): {e}")
    except Exception as e:
        db.rollback()
        print(f"DB 적재 오류: {e}")
    finally:
        db.close()