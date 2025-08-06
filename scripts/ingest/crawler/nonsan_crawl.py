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

def crawl_nonsan_scholarships_to_json(base_url: str, pickle_file: str = 'nonsan_links.pkl', timeout: int = 5) -> List[Dict]:
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
        table = soup.find('table')
        if not table:
            logger.warning("테이블 없음")
            return converted_data

        # 테이블의 행(tr) 추출, 헤더 행 제외
        rows = table.find_all('tr')[1:]  # 첫 번째 행은 헤더
        logger.info(f"테이블 행 수: {len(rows)}")

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            # 제목과 링크 (두 번째 셀에 <a> 태그)
            title_cell = cells[1]  # 제목은 두 번째 열
            link_tag = title_cell.find('a', href=True)
            if not link_tag:
                continue
            href = link_tag['href']
            if not href.startswith('http'):
                href = "https://nonsan.go.kr/kor/html/sub03/030101.html" + href
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
            title_element = soup.select_one('div.bd_detail_tit > h2')  # 논산시청 상세 페이지 제목 셀렉터
            title = title_element.text.strip() if title_element else "제목 없음"
            logger.info(f"추출된 제목: {title}")

            # 날짜 추출 (작성일)
            date_element = soup.select_one('div.bd_detail_tit > ul.info > li.date')  # 작성일 셀렉터
            date_text = date_element.text.strip() if date_element else ""
            if date_text:
                # YYYY.MM.DD -> YYYY-MM-DD
                date_text = date_text.replace('.', '-')
                update_date = date_text
            else:
                logger.warning("날짜 데이터 없음")

            # 본문 추출 (지정 셀렉터의 모든 p 태그, 개별 처리)
            content_tags = soup.select('#txt > div.bd_container.bd_detail.bd_detail_basic > div.bd_detail_content > div > p')
            if not content_tags:
                content_text = "해당없음"
                details = "해당없음"
            else:
                # 각 p 태그를 개별적으로 파싱
                key_value = {}
                additional_details = []  # 나머지 부분 저장
                current_key = None
                for p in content_tags:
                    line = p.text.strip()
                    if line.startswith('○ '):
                        line = line.strip('○ ').strip()
                    if ':' in line:
                        parts = line.split(':', 1)
                        key = parts[0].strip()
                        value = parts[1].strip() if len(parts) > 1 else ""
                        key_value[key] = value
                        current_key = key
                    elif line.startswith('- ') or line.startswith('* ') or line.startswith('→ '):
                        if current_key:
                            key_value[current_key] += '\n' + line
                        else:
                            additional_details.append(line)
                    elif line.startswith('※ '):
                        additional_details.append(line)
                    else:
                        # 기타 줄 (e.g., 서론 부분)
                        if line:
                            additional_details.append(line)

                details = '\n'.join(additional_details) if additional_details else ""

            # 파싱된 값 매핑
            specific_qual = key_value.get('신청자격', "※ 자세한 사항은 기관 홈페이지 참조")
            select_method = key_value.get('신청방법', "※ 자세한 사항은 기관 홈페이지 참조")

            if '신청기간' in key_value:
                value = key_value['신청기간']
                match = re.match(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\(\w+\)\s*~\s*(\d{1,2})\.\s*(\d{1,2})\.\(\w+\)', value)
                if match:
                    year = match.group(1)
                    start_month = match.group(2).zfill(2)
                    start_day = match.group(3).zfill(2)
                    end_month = match.group(4).zfill(2)
                    end_day = match.group(5).zfill(2)
                    start_date = f"{year}-{start_month}-{start_day}"
                    end_date = f"{year}-{end_month}-{end_day}"

            else:
                start_date = "2000-00-00"
                end_date = "2000-00-00"

            # 기준일
            update_date = date.today()

            # 선발인원 상세내용 (본문에서 키워드 검색)
            recipients_num = "0명"
            recipients_match = re.search(r'선발\s*인원\s*:\s*(\d+)', '\n'.join(key_value.values()), re.IGNORECASE)
            if recipients_match:
                recipients_num = recipients_match.group(1) + "명"

            # 학년구분 (본문에서 키워드 검색)
            year_num = "해당없음"
            year_match = re.search(r'학년\s*:\s*(\d+)', '\n'.join(key_value.values()), re.IGNORECASE)
            if year_match:
                year_num = year_match.group(1) + "학년"

            # 지원 내용 (본문에서 키워드 검색)
            support_detail = "0만원"
            support_match = re.search(r'지원\s*금액\s*:\s*(\d+)', '\n'.join(key_value.values()), re.IGNORECASE)
            if support_match:
                support_detail = support_match.group(1) + "만원"

            # OpenAPI 형식 딕셔너리 생성
            item = {
                "번호": i + 1,
                "대학구분": "4년제(5~6년제포함)",  # 논산시청 장학금은 대학 대상으로 가정
                "모집시작일": start_date,
                "모집종료일": end_date,
                "상품구분": ProductType.SCHOLARSHIP.value,
                "상품명": title,
                "선발방법 상세내용": select_method,
                "선발인원 상세내용": recipients_num,
                "성적기준 상세내용": details,
                "소득기준 상세내용": details,
                "운영기관구분": ProviderType.LOCAL_GOV.value,  # 논산시청은 지자체
                "운영기관명": "논산시청",
                "자격제한 상세내용": "※ 자세한 사항은 기관 홈페이지 참조",
                "제출서류 상세내용": "※ 자세한 사항은 기관 홈페이지 참조",
                "지역거주여부 상세내용": "논산시",
                "지원내역 상세내용": support_detail,
                "추천필요여부 상세내용": "해당없음",
                "특정자격 상세내용": specific_qual,
                "학과구분": "제한없음",
                "학년구분": year_num,
                "학자금유형구분": "기타",
                "홈페이지 주소": href,
                "데이터 기준일자": update_date
            }
            converted_data.append(item)
            time.sleep(1)
        except requests.RequestException as e:
            logger.error(f"링크 처리 중 오류: {href}, 오류: {e}")

    # 새로운 링크 저장
    old_links.extend(new_links)
    with open(pickle_file, 'wb') as f:
        pickle.dump(old_links, f)

    # 결과 출력
    for link, title in new_links:
        logger.info(f"Title: {title}, Link: {link}")

    return converted_data

if __name__ == "__main__":
    base_url = "https://nonsan.go.kr/kor/html/sub03/030101.html?skey=title&sval=%EC%9E%A5%ED%95%99%ED%9A%8C&page_size=10"
    json_data = crawl_nonsan_scholarships_to_json(base_url)
    logger.info(f"변환된 JSON 데이터: {json_data}")