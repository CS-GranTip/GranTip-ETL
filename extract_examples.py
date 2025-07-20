import json
from typing import List, Dict, Any

from scripts.ingest.openapi_collector import collect_data
from scripts.ingest.preprocess.data_cleaner import clean_raw_data, FIELDS_WITH_NOTES


def split_detail_fields(cleaned_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    정제된 데이터에서 '상세내용' 필드의 값을 '○' 기호를 기준으로 분리하여 리스트로 변환합니다.

    :param cleaned_rows: data_cleaner를 거친 데이터 딕셔너리의 리스트
    :return: '상세내용' 필드가 분리된 데이터 딕셔너리의 리스트
    """
    processed_rows = []
    
    # data_cleaner에 정의된 '상세내용' 필드 리스트를 사용합니다.
    detail_field_keys = FIELDS_WITH_NOTES

    for row in cleaned_rows:
        processed_row = row.copy()
        for key in detail_field_keys:
            # 해당 키가 row에 있고, 값이 문자열인 경우에만 처리
            if key in processed_row and isinstance(processed_row[key], str):
                value = processed_row[key]
                
                # "○ "를 기준으로 분리하고, 각 항목의 앞뒤 공백을 제거합니다.
                # 분리 후 내용이 없는 빈 문자열은 리스트에서 제외합니다.
                split_list = [part.strip() for part in value.split('○') if part.strip()]
                
                processed_row[key] = split_list
        
        processed_rows.append(processed_row)
        
    return processed_rows


def run_pipeline():
    """
    데이터 수집, 정제, 추가 처리 및 JSON 출력 파이프라인을 실행합니다.
    """
    print("데이터 처리 파이프라인을 시작합니다.")

    # 1. 데이터 수집
    print("\n[1/4] OpenAPI로부터 데이터를 수집합니다...")
    raw_data = collect_data(page=1, perPage=10)
    if not raw_data:
        print("데이터 수집에 실패했습니다. 파이프라인을 중단합니다.")
        return
    print(f"{len(raw_data)}개의 원본 데이터를 수집했습니다.")

    # 2. 기본 데이터 정제
    print("\n[2/4] 수집된 데이터의 기본 정제를 수행합니다...")
    cleaned_data = clean_raw_data(raw_data)
    print("기본 정제가 완료되었습니다.")

    # 3. '상세내용' 필드 분리
    print("\n[3/4] '상세내용' 필드를 리스트로 분리합니다...")
    final_data = split_detail_fields(cleaned_data)
    print("'상세내용' 필드 분리가 완료되었습니다.")

    # 4. 최종 결과를 JSON으로 출력
    print("\n[4/4] 최종 처리된 결과를 JSON 형식으로 출력합니다.")
    print("-" * 50)
    
    # JSON을 예쁘게 출력 (indent=4, 한글 깨짐 방지)
    pretty_json = json.dumps(final_data, indent=4, ensure_ascii=False)
    print(pretty_json)
    
    print("-" * 50)
    print("모든 파이프라인 작업이 성공적으로 완료되었습니다.")


if __name__ == "__main__":
    run_pipeline()