import requests
from bs4 import BeautifulSoup
import re
import time
import pickle
import logging
from datetime import date
from enum import Enum
from typing import List, Dict

class ProviderType(str, Enum):
    LOCAL_GOV = "지자체(출자출연기관)"
    PUBLIC_ORG = "공공기관"
    ETC = "기타"

class ProductType(str, Enum):
    SCHOLARSHIP = "장학금"
    LOAN = "학자금"

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def crawl_suwon_scholarships_to_json(base_url: str, pickle_file: str = 'suwon_links.pkl', timeout: int = 5) -> List[Dict]:
    """
    논산시청 장학금 공지 페이지를 크롤링하여 OpenAPI 형식(JSON)으로 변환합니다.
    
    :param base_url: 게시물 목록 페이지 URL
    :param pickle_file: 저장할 pickle 파일 경로
    :param timeout: 요청 타임아웃 (초)
    :return: List[Dict] - OpenAPI 형식의 JSON 데이터 리스트 (Scholarship 모델 필드에 매핑)
    """
    # 기존 링크 로드
    try:
        with open(pickle_file, 'rb') as f:
            old_links = pickle.load(f)
    except FileNotFoundError:
        old_links = []
        logger.info(f"Pickle 파일 {pickle_file}이 없어 새로 생성합니다.")

    post_links = []
    converted_data = []

    # 게시물 링크 수집 (단일 페이지)
    try:
        response = requests.get(base_url, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 테이블 찾기
        table = soup.select_one('#content > div.content_data > div.data_1200 > div > table.tb4')
        if not table:
            logger.warning("테이블 없음")
            return converted_data

        # 테이블의 행(tr) 추출, 헤더 행 제외
        rows = table.find_all('tr')[1:]  # 첫 번째 행은 헤더
        logger.info(f"테이블 행 수: {len(rows)}")

        for row in rows:
            types_element = row.select_one('td:nth-child(2)')
            types = types_element.text.strip() if types_element else ''
            if '대학생' not in types:
                continue
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            # 제목과 링크 (두 번째 셀에 <a> 태그)
            title_cell = cells[2]  # 제목은 세 번째 열
            link_tag = title_cell.find('a', href=True)
            if not link_tag:
                continue
            href = link_tag['href']
            if not href.startswith('http'):
                href = "https://suwon4u.or.kr/?p=21&page=2&page=1" + href
            title = link_tag.text.strip()
            post_links.append((href, title))
            logger.info(f"수집된 링크: {href}, 제목: {title}")

        time.sleep(1)
    except requests.RequestException as e:
        logger.error(f"페이지 로드 실패: {e}")
        return converted_data

    # 새로운 링크만 처리
    new_links = [(href, title) for href, title in post_links if href not in old_links]
    logger.info(f"새로운 링크 수: {len(new_links)}")

    for i, (href, title) in enumerate(new_links):
        try:
            response = requests.get(href, timeout=timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 제목 추출 (상세 페이지의 제목)
            title_element = soup.select_one('#b_view > tbody > tr:nth-child(1) > th > div > div.m_tit')  # 수원 상세 페이지 제목 셀렉터
            title = title_element.text.strip() if title_element else "제목 없음"
            logger.info(f"추출된 제목: {title}")

            # 날짜 추출 (신청일)
            date_element = soup.select_one('#b_view > tbody > tr:nth-child(1) > th > div > div.etc > span')  # 신청일 셀렉터
            date_text = date_element.get_text().strip() if date_element else ""
            if date_text:
                # 정규 표현식으로 "YYYY-MM-DD HH:MM ~ YYYY-MM-DD HH:MM" 파싱
                match = re.search(r'(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}\s+~\s+(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}', date_text)
                if match:
                    start_date = match.group(1)  # 예: "2025-08-05"
                    end_date = match.group(2)  # 예: "2025-08-12"
                else:
                    start_date = "2025-01-01"
                    end_date = "2025-12-31"
                    logger.warning(f"날짜 형식 파싱 실패: {date_text}")
            else:
                start_date = "2025-01-01"
                end_date = "2025-12-31"
                logger.warning("날짜 데이터 없음")
        except Exception as e:
            start_date = "2025-01-01"
            end_date = "2025-12-31"
            logger.warning(f"날짜 추출 실패: {e}")

        # 기준일 추출
        try:
            update_locator = soup.select_one('#su_write_pageing > table > tbody > tr:nth-child(2) > td > span')
            update_date = update_locator.text.strip() if update_locator else date.today()
        except Exception as e:
            update_date = date.today()
            logger.warning(f"데이터 기준 일자 추출 실패: {e}")

        # 지원내용
        try:
            spdetail_locator = soup.select_one('#b_view > tbody > tr:nth-child(2) > td > div > table > tbody > tr:nth-child(3) > td')
            support_detail = spdetail_locator.text.strip() if spdetail_locator else "해당없음"
        except Exception as e:
            support_detail = "해당없음"
            logger.warning(f"지원 내용 추출 실패: {e}")
        # 상세자격
        try:
            detail_locator = soup.select_one('#b_view > tbody > tr:nth-child(2) > td > div > table > tbody > tr:nth-child(4) > td')
            details = detail_locator.text.strip() if detail_locator else "해당없음"
        except Exception as e:
            details = "해당없음"
            logger.warning(f"상세 내용 추출 실패: {e}")
        # OpenAPI 형식 딕셔너리 생성
        item = {
            "번호": i + 1,
            "대학구분": "4년제(5~6년제포함)",  # 논산시청 장학금은 대학 대상으로 가정
            "모집시작일": start_date,
            "모집종료일": end_date,
            "상품구분": ProductType.SCHOLARSHIP.value,
            "상품명": title,
            "선발방법 상세내용": "※ 자세한 사항은 기관 홈페이지 참조",
            "선발인원 상세내용": "00명",
            "성적기준 상세내용": details,
            "소득기준 상세내용": details,
            "운영기관구분": ProviderType.LOCAL_GOV.value,  # 논산시청은 지자체
            "운영기관명": "논산시청",
            "자격제한 상세내용": "※ 자세한 사항은 기관 홈페이지 참조",
            "제출서류 상세내용": "※ 자세한 사항은 기관 홈페이지 참조",
            "지역거주여부 상세내용": "논산시",
            "지원내역 상세내용": support_detail,
            "추천필요여부 상세내용": "해당없음",
            "특정자격 상세내용": "해당없음",
            "학과구분": "해당없음",
            "학년구분": "해당없음",
            "학자금유형구분": "기타",
            "홈페이지 주소": href,
            "데이터 기준일자": update_date
        }
        converted_data.append(item)
        time.sleep(1)

    # 새로운 링크 저장
    old_links.extend(new_links)
    with open(pickle_file, 'wb') as f:
        pickle.dump(old_links, f)

    # 결과 출력
    for link, title in new_links:
        logger.info(f"Title: {title}, Link: {link}")

    return converted_data

if __name__ == "__main__":
    base_url = "https://suwon4u.or.kr/?p=21&page=2&page=1"
    json_data = crawl_suwon_scholarships_to_json(base_url)
    logger.info(f"변환된 JSON 데이터: {json_data}")