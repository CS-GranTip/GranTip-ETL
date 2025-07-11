def transform_data(cleaned_data):
    """
    기초 전처리된 데이터를 받아 비즈니스 로직을 적용하고 최종 형태로 변환합니다.
    """
    print("데이터 변환(비즈니스 로직 적용)을 시작합니다.")
    # TODO: 장학금 유형별 카테고리 매핑 로직 추가
    # TODO: 추천 점수 산정 로직(score 함수) 적용
    # TODO: 모집 기간이 지난 항목 필터링
    pass

if __name__ == "__main__":
    # 테스트용 샘플 데이터
    sample_data = {"title": "테스트", "conditions": "4년제 대학생"}
    transform_data(sample_data)