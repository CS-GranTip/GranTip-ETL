import asyncio
from playwright.async_api import async_playwright, Playwright, TimeoutError
import json
import re
import time
import pickle
import logging
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Dict

class ProviderType(str, Enum):
    LOCAL_GOV = "지자체(출자출연기관)"
    PUBLIC_ORG = "공공기관"
    ETC = "기타"

class ProductType(str, Enum):
    SCHOLARSHIP = "장학금"
    LOAN = "학자금"

class ScholarshipCategory(str, Enum):
    LOCAL = "LOCAL"
    SPECIALTY = "SPECIALTY"
    GRADE = "GRADE"
    INCOME = "INCOME"
    DISABILITY = "DISABILITY"
    ETC = "ETC"

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def crawl_dreamspon_scholarships_to_json(base_url: str, list_url: str, pickle_file: str = 'seoul_links.pkl', timeout: int = 30000) -> List[Dict]:
    """
    드림스폰 장학금 공지 페이지를 크롤링하여 OpenAPI 형식(JSON)으로 변환합니다.
    :param base_url: 기본 URL (예: https://www.dreamspon.com)
    :param list_url: 목록 페이지 URL (예: /scholarship/list.html?&sch_type=all&sch_key=대학생)
    :param pickle_file: 저장할 pickle 파일 경로
    :param timeout: 페이지 로드 타임아웃 (밀리초 단위)
    :return: List[Dict] - OpenAPI 형식의 JSON 데이터 리스트 (Scholarship 모델 필드에 매핑)
    """
    async with async_playwright() as playwright:
        # 기존 링크 로드
        try:
            with open(pickle_file, 'rb') as f:
                old_links = pickle.load(f)
        except FileNotFoundError:
            old_links = []
            logger.info(f"Pickle 파일 {pickle_file}이 없어 새로 생성합니다.")
        
        post_links = []
        converted_data = []
        
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 로그인 페이지로 이동
            login_url = f"{base_url}/member/login.html"
            await page.goto(login_url, timeout=timeout)
            await page.wait_for_load_state("load")
            # 로그인 폼 입력
            await page.locator("#mbr_id").fill("sucheoliking@gmail.com", timeout=timeout)
            await page.locator("#pwd_in").fill("cjftntpal123!", timeout=timeout)
            await page.locator(".btn_login").click(timeout=timeout)
            await page.wait_for_timeout(1000)
            
            # 장학금 목록 페이지로 이동
            full_list_url = f"{base_url}{list_url}" if list_url.startswith('/') else list_url
            await page.goto(full_list_url, timeout=timeout)
            await page.wait_for_load_state("load")
            
            # 페이지네이션 루프
            post_links = []

            while True:
                # pager 요소를 매번 새로 쿼리 (페이지 변경 후 업데이트)
                pager_selector = 'body > div.wrap > div.container > div.column_wrap.first > div.column_left > div.pager'
                pager = await page.query_selector(pager_selector)
                
                if not pager:
                    logger.warning("Pager 요소를 찾을 수 없습니다.")
                    break
                
                # 목록 로드 대기
                await page.locator("div.bo_table").first.wait_for(timeout=10000)
                links = await page.locator("body > div.wrap > div.container > div.column_wrap.first > div.column_left > div.bo_table > table > tbody > tr").all()
                
                # 이번 페이지에서 수집된 링크 수를 추적하기 위한 변수
                collected_this_page = 0
                
                for item in links:  # item은 각 tr 요소
                    try:
                        # 모집마감 상태 확인: td.td_day > span.state.bgGray가 있으면 스킵
                        status_span_locator = item.locator('td.td_day > span.state.bgGray')
                        if await status_span_locator.count() > 0:
                            continue
                        
                        # 상태가 모집마감이 아니면 링크와 제목 추출
                        title_link_locator = item.locator('td.td_subject > p > a')
                        if await title_link_locator.count() > 0:
                            title_link = title_link_locator.first  # first는 속성으로 호출 (괄호 없음)
                            title = await title_link.inner_text()
                            href = await title_link.get_attribute("href")
                            if not href.startswith('http'):
                                href = f"{base_url}{href}"
                            post_links.append((href, title))
                            logger.info(f"수집된 링크: {href}, 제목: {title}")
                            collected_this_page += 1
                    except Exception as e:
                        logger.warning(f"Error parsing item: {e}")
                        continue
                time.sleep(1)
                
                # 이번 페이지에서 하나도 수집하지 못했다면 루프 종료
                if collected_this_page == 0:
                    logger.info("이번 페이지에서 수집된 링크가 없으므로 크롤링을 종료합니다.")
                    break
                
                # 다음 페이지로 이동
                try:
                    current_page = await pager.query_selector('a.current')
                    if current_page:
                        page_num = await current_page.inner_text()
                        page_num = int(page_num.strip())  # 문자열을 정수로 변환
                        
                        # 다음 페이지 번호 계산 및 셀렉터 생성
                        next_page_num = page_num + 1
                        target_selector = f'a[href="?page={next_page_num}"]'
                        target_link = await pager.query_selector(target_selector)
                        
                        if target_link:
                            await target_link.click()
                            await page.wait_for_load_state('networkidle')  # 페이지 로드 대기
                        else:
                            logger.info("다음 페이지 링크가 없습니다. 크롤링 종료.")
                            break
                    else:
                        logger.warning("현재 페이지(a.current)를 찾을 수 없습니다.")
                        break
                except Exception as e:
                    logger.error(f"페이지 이동 중 오류: {e}")
                    break  # 오류 발생 시 종료
        finally:
            # 브라우저 종료 전에 상세 페이지 파싱
            # 새로운 링크만 처리 (old_links가 href 리스트라고 가정, 필요 시 수정)
            new_links = [(href, title) for href, title in post_links if href not in old_links]
            logger.info(f"새로운 링크 수: {len(new_links)}")
            
            for i, (href, title) in enumerate(new_links):
                try:
                    # 상세 페이지로 이동
                    await page.goto(href, timeout=timeout)
                    await page.wait_for_load_state('networkidle')
                    
                    ps = await page.locator("#tab1s > dl > dd > p").all()
                    
                    scholarship_type = ScholarshipCategory.ETC.value

                    for items in ps:
                        texts = items.locator("span > strong")
                        if await texts.count() > 0:
                            text_content = await texts.inner_text()  # await 추가
                            cleaned_text = text_content.replace("•", "").strip()  # bullet 제거
                            etc_need = ""
                            recommand_need = ""
                            grade_need = ""
                            region_need = ""
                            income_need = ""
                            if "신청기간" in cleaned_text:
                                # 다음 아이템의 텍스트를 date_text로 설정 (ps 리스트에서 다음 인덱스 접근 필요)
                                print("신청기간파싱")
                                current_index = ps.index(items)
                                if current_index + 1 < len(ps):
                                    next_item = ps[current_index + 1]
                                    date_text = await next_item.inner_text()  # 다음 <p> 전체 텍스트 추출
                                else:
                                    date_text = ""  # 다음 아이템 없으면 빈 문자열
                                start_date = "2025-01-01"
                                end_date = "2025-12-31"
                                try:
                                    # 지정된 형식 "YYYY. MM. DD. ~ YYYY. MM. DD."에 맞춘 정규표현식 (월/일 2자리, 공백/점 허용)
                                    match = re.search(r'(\d{4}\.\s*\d{2}\.\s*\d{2}\.)\s*~\s*(\d{4}\.\s*\d{2}\.\s*\d{2}\.)', date_text)
                                    if match:
                                        # 추출된 문자열 정리: 공백 제거, 점을 -로 변환, 끝 점 제거
                                        start_str = match.group(1).strip('.').replace(' ', '').replace('.', '-')
                                        end_str = match.group(2).strip('.').replace(' ', '').replace('.', '-')
                                        # datetime으로 파싱하여 YYYY-MM-DD 형식으로 변환
                                        start_date = datetime.strptime(start_str, "%Y-%m-%d").strftime("%Y-%m-%d")
                                        end_date = datetime.strptime(end_str, "%Y-%m-%d").strftime("%Y-%m-%d")
                                    print(start_date, end_date)
                                except ValueError as ve:
                                    logger.warning(f"날짜 형식 오류: {ve} - 기본값 사용")
                                except Exception as e:
                                    logger.warning(f"날짜 추출 실패: {e}")
                        
                            #선발인원 추출
                            elif "선발인원" in cleaned_text:
                                print("선발인원파싱")
                                # 다음 아이템의 텍스트를 select_num로 설정
                                current_index = ps.index(items)
                                if current_index + 1 < len(ps):
                                    next_item = ps[current_index + 1]
                                    select_num = await next_item.inner_text()  # 다음 <p> 전체 텍스트 추출
                                else:
                                    select_num = "0명"  # 다음 아이템 없으면 빈 문자열
                                
                            #장학혜택 추출
                            elif "장학혜택" in cleaned_text:
                                print("장학혜택파싱")
                                current_index = ps.index(items)
                                extracted_texts = []
                                for j in range(current_index + 1, len(ps)):
                                    next_item = ps[j]
                                    if await next_item.locator("span > strong").count() > 0:
                                        break  # 다음 레이블(<span> 있는 <p>) 만나면 중단
                                    extracted_texts.append((await next_item.inner_text()).strip())
                                scholarship_benefit = ' '.join(extracted_texts) if extracted_texts else "해당없음"
                                
                            #접수방법 추출
                            elif "접수방법" in cleaned_text:
                                print("접수방법파싱")
                                current_index = ps.index(items)
                                extracted_texts = []
                                for j in range(current_index + 1, len(ps)):
                                    next_item = ps[j]
                                    if await next_item.locator("span > strong").count() > 0:
                                        break  # 다음 레이블(<span> 있는 <p>) 만나면 중단
                                    extracted_texts.append((await next_item.inner_text()).strip())
                                reception_method = ' '.join(extracted_texts) if extracted_texts else "해당없음"

                            #신청자격 추출
                            elif "신청자격" in cleaned_text:
                                print("신청자격파싱")
                                current_index = ps.index(items)
                                extracted_texts = []
                            
                                scholarship_type = None  # 필요 시 기본값 설정, ScholarshipCategory enum 가정
                                for j in range(current_index + 1, len(ps)):
                                    next_item = ps[j]
                                    if await next_item.locator("span > strong").count() > 0:
                                        break  # 다음 레이블(<span> 있는 <p>) 만나면 중단
                                    if await next_item.locator("span > b").count() > 0:
                                        next_text = await next_item.inner_text()
                                        if re.search("기타", next_text):
                                            etc_need = next_text.strip()  # 기타 내용 추가
                                        if re.search("추천", next_text):
                                            recommand_need = next_text.strip()  # 추천 내용 추가
                                        if re.search("성적", next_text):
                                            grade_need = next_text.strip()  # 성적 내용 추가
                                            scholarship_type = ScholarshipCategory.GRADE.value
                                        if re.search("지역", next_text):
                                            region_need = next_text.strip()  # 지역 내용 추가
                                            scholarship_type = ScholarshipCategory.LOCAL.value
                                        if re.search("소득", next_text):
                                            income_need = next_text.strip()  # 소득 내용 추가
                                            scholarship_type = ScholarshipCategory.INCOME.value
                                total_method = ' '.join(extracted_texts) if extracted_texts else "해당없음"

                            #지원대상 추출
                            elif "지원대상" in cleaned_text:
                                print("지원대상파싱")
                                current_index = ps.index(items)
                                extracted_texts = []
                                for j in range(current_index + 1, len(ps)):
                                    next_item = ps[j]
                                    if await next_item.locator("span > strong").count() > 0:
                                        break  # 다음 레이블(<span> 있는 <p>) 만나면 중단
                                    extracted_texts.append((await next_item.inner_text()).strip())
                                apply_method = ' '.join(extracted_texts) if extracted_texts else "해당없음"


                    if "학자금" in title:
                        product_type = ProductType.SCHOLARSHIP.value
                    else:
                        product_type = ProductType.LOAN.value
                    
                    memo = page.locator("#scholarship_v > div.view_top_bx > div.key_summary > div.memo")
                    if await memo.count() > 0:
                        memo_text = await memo.inner_text()  # await 추가

                    name = page.locator("#scholarship_v > div.view_top_bx > div.v_hd > div.name")
                    if await name.count() > 0:
                        name_text = await name.inner_text()  # await 추가
                                    # 기준일
                    update_date = date.today()
                    
                    # OpenAPI 형식 딕셔너리 생성
                    item = {
                        "번호": i + 1,
                        "대학구분": "4년제(5~6년제포함)",
                        "모집시작일": start_date,
                        "모집종료일": end_date,
                        "상품구분": product_type,
                        "상품명": title,
                        "선발방법 상세내용": "※ 자세한 사항은 기관 홈페이지 참조",
                        "선발인원 상세내용": select_num,
                        "성적기준 상세내용": grade_need,
                        "소득기준 상세내용": income_need,
                        "운영기관구분": ProviderType.ETC.value,
                        "운영기관명": name_text,
                        "자격제한 상세내용": total_method,
                        "제출서류 상세내용": "※ 자세한 사항은 기관 홈페이지 참조",
                        "지역거주여부 상세내용": memo_text + region_need, #지역내용이 있을수도 없을수도
                        "지원내역 상세내용": scholarship_benefit,
                        "추천필요여부 상세내용": recommand_need,
                        "특정자격 상세내용": etc_need,
                        "학과구분": "해당없음",
                        "학년구분": "해당없음",
                        "학자금유형구분": "해당없음",
                        "홈페이지 주소": href,
                        "데이터 기준일자": update_date
                    }
                    converted_data.append(item)
                    await asyncio.sleep(1)  # 비동기 지연
                except Exception as e:
                    logger.error(f"상세 페이지 파싱 오류 ({href}): {e}")
                    continue
            
            # 브라우저 종료
            await browser.close()
            
            # 새로운 링크 저장 (old_links 업데이트, href만 저장 가정)
            old_links.extend([href for href, title in new_links])
            with open(pickle_file, 'wb') as f:
                pickle.dump(old_links, f)
            
            # 결과 출력
            for href, title in new_links:
                logger.info(f"Title: {title}, Link: {href}")
            
            return converted_data
        

if __name__ == "__main__":
    import asyncio
    base_url = "https://www.dreamspon.com"
    list_url = "/scholarship/list.html?&sch_type=all&sch_key=대학생"
    json_data = asyncio.run(crawl_dreamspon_scholarships_to_json(base_url, list_url))
    logger.info(f"변환된 JSON 데이터: {json_data}")