from datetime import date
from pydantic import BaseModel, Field

class Scholarship(BaseModel):
    """DB에 저장될 최종 장학금 데이터의 스키마(규칙)를 정의합니다."""
    
    # TODO: 프로젝트에 필요한 필드들 정의

# 이 파일은 다른 파일에서 import하여 사용됩니다.
if __name__ == "__main__":
    # 샘플 데이터
    sample_data = {
        "title": "기본 장학금",
        "provider": "기본 재단",
        "amount": 1000000,
        "end_date": "2025-09-30"
    }
    
    # 샘플 데이터로 모델 인스턴스 생성
    scholarship_instance = Scholarship(**sample_data)
    
    # 생성된 인스턴스 출력
    print("✅ Pydantic 모델 테스트 성공:")
    print(scholarship_instance)