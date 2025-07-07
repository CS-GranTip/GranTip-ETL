def clean_data(raw_data):
    """
    수집된 원시 데이터를 받아 기초 전처리를 수행합니다.
    (예: HTML 태그 제거, 불필요한 공백 제거, 기본 형식 통일)
    """
    print("데이터 기초 전처리를 시작합니다.")
    # TODO: Pandas DataFrame을 사용하여 데이터 정제 로직 추가
    pass

if __name__ == "__main__":
    # 테스트용 샘플 데이터
    sample_data = {"title": "  <b>테스트</b>  ", "amount": "100만원"}
    clean_data(sample_data)