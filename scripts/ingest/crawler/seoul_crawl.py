from playwright.sync_api import sync_playwright
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

def crawl_seoul_scholarships_to_json(base_url: str, list_url: str, pickle_file: str = 'seoul_links.pkl', timeout: int = 30000) -> List[Dict]:
    """
    서울장학재단 장학금 신청 페이지를 크롤링하여 OpenAPI 형식(JSON)으로 변환합니다.
    
    :param base_url: 게시물 목록 페이지 URL
    :param list_url: 상세 페이지 URL 템플릿
    :param pickle_file: 저장할 pickle 파일 경로
    :param timeout: 페이지 로드 타임아웃 (ms)
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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            logger.info(f"목록 페이지 로드 중: {base_url}")
            page.goto(base_url, timeout=timeout)
            page.wait_for_load_state("networkidle")
            page.wait_for_selector('a.link', timeout=timeout)  # 게시물 링크 대기
            posts = page.locator('a.link')
            logger.info(f"게시물 수: {posts.count()}")

            hrefs = []
            for i in range(posts.count()):
                post = posts.nth(i)
                onclick = post.get_attribute('onclick')
                if onclick:
                    match = re.search(r"fn_edit\('(.*?)'\)", onclick)
                    if match:
                        idx = match.group(1)
                        href = f"{list_url}?idx={idx}&act=%5Bobject+HTMLInputElement%5D&searchValue4=&searchValue1=&searchValue2=&eSearchValue1=&searchValue3=&searchKeyword=&pageIndex=1"
                        hrefs.append((href, idx))
                        logger.info(f"수집된 링크: {href}")

            logger.info(f"총 수집된 링크 수: {len(hrefs)}")

            for i, (href, idx) in enumerate(hrefs):
                try:
                    logger.info(f"상세 페이지 로드 중: {href}")
                    page.goto(href, timeout=timeout)
                    page.wait_for_load_state("networkidle")
                    title_element = page.locator('#cmmnForm > div.page_list.ann_view > div.fixed_box > div > h1')
                    title = title_element.inner_text().strip() if title_element else "제목 없음"
                    logger.info(f"추출된 제목: {title}")

                    # 날짜 추출 및 파싱
                    try:
                        date_locator = page.locator('#cmmnForm > div.page_list.ann_view > ul > li:nth-child(1) > div > ul > li:nth-child(3) > div.dd')
                        date_text = date_locator.inner_text().strip() if date_locator.count() > 0 else ""
                        if date_text:
                            # 정규 표현식으로 "YYYY-MM-DD HH:MM ~ YYYY-MM-DD HH:MM" 파싱
                            match = re.match(r'(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}\s+~\s+(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}', date_text)
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

                    #기준일 추출
                    try:
                        update_locator = page.locator('#cmmnForm > div.page_list.ann_view > div.fixed_box > div > ul.board_date > li:nth-child(3) > span.dd')
                        update_date = update_locator.inner_text().strip() if update_locator.count() > 0 else date.today()
                    except Exception as e:
                        update_date = date.today()
                        logger.warning(f"데이터 기준 일자 추출 실패: {e}")

                    #선발인원 상세내용 추출
                    try:
                        recipients_locator = page.locator('#cmmnForm > div.page_list.ann_view > ul > li:nth-child(1) > div > ul > li:nth-child(6) > div.dd')
                        recipients_num = recipients_locator.inner_text().strip() if recipients_locator.count() > 0 else "0명"
                    except Exception as e:
                        recipients_num = "0명"
                        logger.warning(f"선발인원 상세내용 추출 실패: {e}")
                    
                    #학년구분 추출
                    try:
                        year_locator = page.locator('#cmmnForm > div.page_list.ann_view > ul > li:nth-child(1) > div > ul > li:nth-child(2) > div.dd')
                        year_num = year_locator.inner_text().strip() if year_locator.count() > 0 else "해당없음"
                    except Exception as e:
                        year_num = "해당없음"
                        logger.warning(f"학년구분 추출 실패: {e}")

                    

                    try:
                        support_locator = page.locator('#cmmnForm > div.page_list.ann_view > ul > li:nth-child(2) > div > ul > li.card_box.b3 > div.tit')
                        support_detail = support_locator.inner_text().strip() if support_locator.count() > 0 else "0만원"
                    except Exception as e:
                        support_detail = "0만원"
                        logger.warning(f"지원 내용 추출 실패: {e}")

                    try:
                        detail_locator = page.locator('#cmmnForm > div.page_list.ann_view > ul > li:nth-child(3) > div > div')
                        details = detail_locator.inner_text().strip() if detail_locator.count() > 0 else "해당없음"
                        details = details.replace('-', '○')
                    except Exception as e:
                        details = "해당없음"
                        logger.warning(f"지원 내용 추출 실패: {e}")

                    # OpenAPI 형식에 맞춘 딕셔너리 생성
                    item = {
                        "번호": i + 1,
                        "대학구분": "4년제(5~6년제포함)",  # 서울장학재단은 주로 대학 대상
                        "모집시작일": start_date,
                        "모집종료일": end_date,
                        "상품구분": ProductType.SCHOLARSHIP.value,
                        "상품명": title,
                        "선발방법 상세내용": "※ 자세한 사항은 기관 홈페이지 참조",
                        "선발인원 상세내용": recipients_num,
                        "성적기준 상세내용": details,
                        "소득기준 상세내용": details,
                        "운영기관구분": ProviderType.PUBLIC_ORG.value,
                        "운영기관명": "서울장학재단",
                        "자격제한 상세내용": "※ 자세한 사항은 기관 홈페이지 참조",
                        "제출서류 상세내용": "※ 자세한 사항은 기관 홈페이지 참조",
                        "지역거주여부 상세내용": "서울",
                        "지원내역 상세내용": support_detail,
                        "추천필요여부 상세내용": "해당없음",
                        "특정자격 상세내용": details,
                        "학과구분": "제한없음",
                        "학년구분": year_num,
                        "학자금유형구분": "기타",
                        "홈페이지 주소": href,
                        "데이터 기준일자": update_date
                    }
                    converted_data.append(item)

                    if href not in [link for link, _ in old_links]:
                        post_links.append((href, title))
                except Exception as e:
                    logger.error(f"링크 처리 중 오류: {href}, 오류: {e}")
                time.sleep(1)
        finally:
            browser.close()

    # 새로운 링크 저장
    new_links = [(href, title) for href, title in post_links if href not in [link for link, _ in old_links]]
    old_links.extend(new_links)
    with open(pickle_file, 'wb') as f:
        pickle.dump(old_links, f)

    # 결과 출력
    for link, title in post_links:
        logger.info(f"Title: {title}, Link: {link}")

    return converted_data

if __name__ == "__main__":
    base_url = "https://www.hissf.or.kr/home/kor/M821806781/scholarship/business/index.do"
    list_url = "https://www.hissf.or.kr/home/kor/M821806781/scholarship/business/view.do"
    json_data = crawl_seoul_scholarships_to_json(base_url, list_url)
    logger.info(f"변환된 JSON 데이터: {json_data}")