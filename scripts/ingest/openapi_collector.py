import requests
import logging 

#로깅 설정(API 호출시 에러 처리)
logging.basicConfig(level=logging.DEBUG) #DEBUG(요청 시작/성공여부 기록), INFO(응답 내용 기록), ERROR(실패 원인 기록)
logger = logging.getLogger(__name__)    #현재 모듈 이름

def collect_data(page, perPage=10):
    """
    특정 페이지의 데이터를 API로부터 가져오는 함수.
    
    :param page: 페이지 번호
    :param per_page: 페이지당 조회할 데이터 수
    :return: API로부터 받은 JSON 데이터
    """
    api_url = "https://api.odcloud.kr/api/15028252/v1/uddi:9398a88a-d06c-4fc4-b230-82b8ec37e304"
    params = {
        "page": str(page),
        "perPage": str(perPage),
        "serviceKey": "SLYz3LVdJuaD2s5Mso1D1hp5D1CN4LNlfdKpPREQVKHHRonBV6VBQlrYRCdh+QbZKYcfPbrCMTgW9pUOnhqQ+w=="
    }
    logger.info("OpenAPI로부터 데이터를 수집합니다.")

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status() #HTTP 오류 발생시 예외 발생

        data = response.json().get('data', [])
        logger.info(f"{page} 페이지에서 {len(data)}개의 데이터를 가져왔습니다.")
        return data
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API 요청 오류:{e}")
        return None
    
def collect_all_data(perPage=100):
    """
    모든 페이지의 데이터를 수집하는 함수.
    
    :param perPage: 페이지당 조회할 데이터 수
    :return: 모든 페이지로부터 수집된 데이터 리스트
    """
    all_data = []
    page = 1
    
    logger.info("OpenAPI로부터 데이터를 수집합니다.")

    while True:
        logger.info(f"{page} 페이지 데이터 수집 시도...")
        data = collect_data(page, perPage)
        
        # 데이터 수집에 실패했거나, 더 이상 데이터가 없는 경우 반복 중단
        if data is None or not data:
            if data is None:
                logger.error(f"데이터 수집 중 오류가 발생하여 중단합니다.")
            else:
                 logger.info("더 이상 가져올 데이터가 없어 수집을 완료했습니다.")
            break
            
        all_data.extend(data) # 수집된 데이터를 전체 리스트에 추가
        page += 1

    logger.info(f"총 {len(all_data)}개의 데이터를 수집했습니다.")
    return all_data


if __name__ == "__main__":
    page_number = 1 #페이지 번호 설정해주기
    data = collect_data(page_number)

    if(data):
        logger.info(f"가져온 데이터: {data}")
    else:
        logger.error("데이터를 가져오지 못했습니다.")