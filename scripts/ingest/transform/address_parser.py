# -*- coding: utf-8 -*-
import re
import requests
import logging
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

# 로깅 설정 (openapi_collector.py에서 복사)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# openapi_collector.py의 collect_data 함수 복사 및 통합
def collect_data(page, perPage=10):
    api_url = "https://api.odcloud.kr/api/15028252/v1/uddi:9398a88a-d06c-4fc4-b230-82b8ec37e304"
    params = {
        "page": str(page),
        "perPage": str(perPage),
        "serviceKey": "SLYz3LVdJuaD2s5Mso1D1hp5D1CN4LNlfdKpPREQVKHHRonBV6VBQlrYRCdh+QbZKYcfPbrCMTgW9pUOnhqQ+w=="
    }
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json().get('data', [])
        logger.info(f"{page} 페이지에서 {len(data)}개의 데이터를 가져왔습니다.")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"API 요청 오류: {e}")
        return None

KOREAN_REGIONS_MAP = {
    # --- 광역자치단체 (시/도) ---
    '서울': '서울특별시',
    '서울특별시': '서울특별시',
    '부산': '부산광역시',
    '부산광역시': '부산광역시',
    '대구': '대구광역시',
    '대구광역시': '대구광역시',
    '인천': '인천광역시',
    '인천광역시': '인천광역시',
    '광주': '광주광역시', # '광주시'와 구분하기 위해 '광주광역시'로 명시
    '광주광역시': '광주광역시',
    '대전': '대전광역시',
    '대전광역시': '대전광역시',
    '울산': '울산광역시',
    '울산광역시': '울산광역시',
    '세종': '세종특별자치시',
    '세종특별자치시': '세종특별자치시',
    '경기': '경기도',
    '경기도': '경기도',
    '충북': '충청북도',
    '충청북도': '충청북도',
    '충남': '충청남도',
    '충청남도': '충청남도',
    '전북': '전북특별자치도',
    '전라북도': '전북특별자치도',
    '전북특별자치도': '전북특별자치도',
    '전북특별자치': '전북특별자치도',
    '전남': '전라남도',
    '전라남도': '전라남도',
    '경북': '경상북도',
    '경상북도': '경상북도',
    '경남': '경상남도',
    '경상남도': '경상남도',
    '강원': '강원특별자치도',
    '강원도': '강원특별자치도',
    '강원특별자치도': '강원특별자치도',
    '강원특별자치': '강원특별자치도',
    '제주': '제주특별자치도',
    '제주도': '제주특별자치도',
    '제주특별자치도': '제주특별자치도',
    '제주특별자치': '제주특별자치도',

    # --- 기초자치단체 (시/군/구) ---
    '가평': '가평군',
    '강남': '강남구',
    '강동': '강동구',
    '강릉': '강릉시',
    '강북': '강북구',
    '강서': '강서구',
    '강진': '강진군',
    '강화': '강화군',
    '거제': '거제시',
    '거창': '거창군',
    '경산': '경산시',
    '경주': '경주시',
    '계룡': '계룡시',
    '계양': '계양구',
    '고령': '고령군',
    '고성': '고성군',
    '고양': '고양시',
    '고창': '고창군',
    '고흥': '고흥군',
    '곡성': '곡성군',
    '공주': '공주시',
    '과천': '과천시',
    '관악': '관악구',
    '광명': '광명시',
    '광산': '광산구',
    '광양': '광양시',
    '광주시': '광주시', # 경기도 광주시
    '광진': '광진구',
    '괴산': '괴산군',
    '구례': '구례군',
    '구로': '구로구',
    '구리': '구리시',
    '구미': '구미시',
    '군산': '군산시',
    '군위': '군위군',
    '군포': '군포시',
    '금산': '금산군',
    '금정': '금정구',
    '금천': '금천구',
    '기장': '기장군',
    '김제': '김제시',
    '김천': '김천시',
    '김포': '김포시',
    '김해': '김해시',
    '나주': '나주시',
    '남구': '남구',
    '남동': '남동구',
    '남양주': '남양주시',
    '남원': '남원시',
    '남해': '남해군',
    '노원': '노원구',
    '논산': '논산시',
    '단양': '단양군',
    '달서': '달서구',
    '달성': '달성군',
    '담양': '담양군',
    '당진': '당진시',
    '대덕': '대덕구',
    '도봉': '도봉구',
    '동대문': '동대문구',
    '동구': '동구',
    '동두천': '동두천시',
    '동래': '동래구',
    '동작': '동작구',
    '동해': '동해시',
    '마포': '마포구',
    '목포': '목포시',
    '무안': '무안군',
    '무주': '무주군',
    '문경': '문경시',
    '미추홀': '미추홀구',
    '밀양': '밀양시',
    '보령': '보령시',
    '보성': '보성군',
    '보은': '보은군',
    '봉화': '봉화군',
    '부산진': '부산진구',
    '부안': '부안군',
    '부여': '부여군',
    '부천': '부천시',
    '부평': '부평구',
    '북구': '북구',
    '사상': '사상구',
    '사천': '사천시',
    '사하': '사하구',
    '산청': '산청군',
    '삼척': '삼척시',
    '상주': '상주시',
    '서구': '서구',
    '서대문': '서대문구',
    '서산': '서산시',
    '서귀포': '서귀포시',
    '서천': '서천군',
    '서초': '서초구',
    '성남': '성남시',
    '성동': '성동구',
    '성북': '성북구',
    '성주': '성주군',
    '속초': '속초시',
    '송파': '송파구',
    '수성': '수성구',
    '수영': '수영구',
    '수원': '수원시',
    '순창': '순창군',
    '순천': '순천시',
    '시흥': '시흥시',
    '신안': '신안군',
    '아산': '아산시',
    '안동': '안동시',
    '안산': '안산시',
    '안성': '안성시',
    '안양': '안양시',
    '양구': '양구군',
    '양산': '양산시',
    '양양': '양양군',
    '양주': '양주시',
    '양천': '양천구',
    '양평': '양평군',
    '여수': '여수시',
    '여주': '여주시',
    '연수': '연수구',
    '연제': '연제구',
    '연천': '연천군',
    '영광': '영광군',
    '영덕': '영덕군',
    '영도': '영도구',
    '영동': '영동군',
    '영등포': '영등포구',
    '영양': '영양군',
    '영월': '영월군',
    '영암': '영암군',
    '영주': '영주시',
    '영천': '영천시',
    '예산': '예산군',
    '예천': '예천군',
    '오산': '오산시',
    '옥천': '옥천군',
    '옹진': '옹진군',
    '완도': '완도군',
    '완주': '완주군',
    '용산': '용산구',
    '용인': '용인시',
    '울릉': '울릉군',
    '울주': '울주군',
    '울진': '울진군',
    '원주': '원주시',
    '유성': '유성구',
    '은평': '은평구',
    '음성': '음성군',
    '의령': '의령군',
    '의성': '의성군',
    '의왕': '의왕시',
    '의정부': '의정부시',
    '이천': '이천시',
    '익산': '익산시',
    '인제': '인제군',
    '임실': '임실군',
    '장성': '장성군',
    '장수': '장수군',
    '장흥': '장흥군',
    '전주': '전주시',
    '정선': '정선군',
    '정읍': '정읍시',
    '제주시': '제주시',
    '제천': '제천시',
    '종로': '종로구',
    '중구': '중구',
    '중랑': '중랑구',
    '증평': '증평군',
    '진도': '진도군',
    '진안': '진안군',
    '진주': '진주시',
    '진천': '진천군',
    '창녕': '창녕군',
    '창원': '창원시',
    '천안': '천안시',
    '철원': '철원군',
    '청도': '청도군',
    '청송': '청송군',
    '청양': '청양군',
    '청주': '청주시',
    '춘천': '춘천시',
    '충주': '충주시',
    '칠곡': '칠곡군',
    '태백': '태백시',
    '태안': '태안군',
    '통영': '통영시',
    '파주': '파주시',
    '평창': '평창군',
    '평택': '평택시',
    '포천': '포천시',
    '포항': '포항시',
    '하남': '하남시',
    '하동': '하동군',
    '함안': '함안군',
    '함양': '함양군',
    '함평': '함평군',
    '합천': '합천군',
    '해남': '해남군',
    '해운대': '해운대구',
    '홍성': '홍성군',
    '홍천': '홍천군',
    '화성': '화성시',
    '화순': '화순군',
    '화천': '화천군',
    '횡성': '횡성군',
}

import re
from typing import Optional, List

def address_parser(text: Optional[str], org_name: Optional[str] = None) -> Optional[List[str]]:
    """
    OpenAPI의 지역거주여부 상세내용을 받아온 후 해당 내용 중에서 주소지만 추출
    예:○ 장학생 선발 공고일 1년 전부터 부모 또는 본인이 청양군에 주소를 두고 거주한 자 > '청양군'
    예:○ 보호자 또는 본인이 선발 공고일 현재 주민등록상 주소지가 광주광역시 남구로 1년 이상 두고 신청 요건을 갖춘 자 > '광주광역시','남구'
    '관내'가 포함된 경우 운영기관명에서 추가로 주소 추출
    """
    if text is None:
        return None
    
    # 텍스트에서 한글 단어 추출
    words = re.findall(r'\b[\uac00-\ud7a3]+\b', text)
    
    matches = []
    for word in words:
        candidates = [region for region in KOREAN_REGIONS_MAP.keys() if word.startswith(region)]
        if candidates:
            # 한 단어에서 여러 후보가 있으면 가장 긴 것을 선택
            longest_region = max(candidates, key=len)
            # 홀수번째(약칭)에 대응하는 전체 이름 매핑
            full_region = KOREAN_REGIONS_MAP[longest_region]
            matches.append(full_region)

    # 동/읍/면 패턴 추출 (text)
    address_pattern = r'(\b\w+동|\b\w+읍|\b\w+면)'
    matches2 = re.findall(address_pattern, text)
    
    # 중복 제거 및 리스트 병합
    unique_addresses = list(dict.fromkeys(matches + matches2))

    # 운영기관명에서 주소 추출
    if org_name:
        org_words = re.findall(r'\b[\uac00-\ud7a3]+\b', org_name)
        for word in org_words:
            candidates = [region for region in KOREAN_REGIONS_MAP.keys() if word.startswith(region)]
            if candidates:
                longest_region = max(candidates, key=len)
                full_region = KOREAN_REGIONS_MAP[longest_region]
                unique_addresses.append(full_region)
        # 동/읍/면 패턴 추출 (org_name)
        org_matches = re.findall(address_pattern, org_name)
        unique_addresses.extend(org_matches)

    # 중복 제거
    unique_addresses = list(dict.fromkeys(unique_addresses))
    return unique_addresses if unique_addresses else None

# 테스트 실행 부분
if __name__ == "__main__":
    # OpenAPI에서 데이터 수집 (페이지 14, 100개 항목 가져옴)
    api_data = collect_data(page=14, perPage=100)
    
    if api_data:
        for item in api_data:
            scholarship_id = item.get('번호', 0)  # ID 추출
            raw_text = item.get('지역거주여부 상세내용', '')  # 텍스트 추출
            org_name = item.get('운영기관명', '')  # 운영기관명 추출
            if raw_text:
                result = address_parser(raw_text, org_name)
                print(f"\n테스트 ID: {scholarship_id}, 입력 텍스트: '{raw_text}', 운영기관명: '{org_name}'")
                print(result)
    else:
        print("API에서 데이터를 가져오지 못했습니다.")