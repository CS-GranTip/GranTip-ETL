def load_to_db(transformed_data):
    """
    변환된 데이터를 받아 DB에 저장(UPSERT)합니다.
    """
    print("데이터베이스에 데이터를 적재합니다.")
    # TODO: SQLAlchemy를 사용하여 DB 연결 및 데이터 삽입/업데이트 로직 추가
    pass

if __name__ == "__main__":
    # 테스트용 샘플 데이터
    sample_data = [{"title": "테스트 장학금", "provider": "테스트 기관"}]
    load_to_db(sample_data)