import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import time
import pickle

#푸른등대 장학금 게시판 페이지
base_url = "https://www.kosaf.go.kr/ko/notice.do?ctgrId1=0000000002&ctgrId2=&searchStr=&searchType=&page={}&pg="

#첫페이지 불러오기
url = base_url.format(1)
try:
    response = requests.get(url, timeout = 5)
    response.raise_for_status()
    soup = BeautifulSoup(response.text,'html.parser')

    #맨 마지막 페이지
    last_page = soup.find('a', href = lambda x: x and 'ctgrId1=0000000002' in x, title = '맨 마지막 페이지로 이동')
    if last_page:
        href = last_page['href']
        parsed_url = urlparse(href)
        query_params = parse_qs(parsed_url.query)
        max_page = int(query_params.get('page',[None])[0])
        print(f"최대페이지:{max_page}")
    else:
        print("최대 페이지 찾기 오류")
        max_page = 5
except requests.RequestException as e:
    print(f"첫 페이지를 못찾았습니다:{e}")
    max_page = 5 

#기존 링크 로드(새로운 게시물만 수집)
try:
    with open('kosaf_links.pkl', 'rb') as f:
        old_links = pickle.load(f)
except:
    old_links = []

#게시물 링크 수집
post_links = []
for page in range(1, 2):
    url = base_url.format(page)
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text,'html.parser')

        #게시물 상세페이지 링크만 대상으로 변경
        posts = soup.find_all('a', href = lambda x: x and 'ctgrId1=0000000002' in x and 'mode=view' in x)
        for post in posts:
            href = post['href']
            if not href.startswith('http'):
                href = "https://www.kosaf.go.kr/ko/notice.do" + href
            title = post.text.strip()
            post_links.append((href, title))
            # print(f"페이지 {page} - 제목: {title}, 링크:{href}")
        time.sleep(1)
        
    except requests.RequestException as e:
        print(f"페이지네이션 오류:{e}")
        continue

new_links = [(link, title) for link, title in post_links if link not in old_links]
for link, title in new_links:
    try:
        response = requests.get(link, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('th', id = 'VIEW_TITLE')
        date_tag = soup.find_all('span', id = 'VIEW_DADATE')
        content_tag = soup.find('td', id = 'VIEW_MCONTENT')
        
        title_text = title_tag.text.strip() if title_tag else title
        date_text = date_tag[1].text.strip() if date_tag else print("날짜정보 불러오기 실패!")

        print(f"게시물 명: {title_text}\n 작성 날짜: {date_text}")
        # content_tag에서 <p> 태그 추출
        contents = content_tag.find_all('p') if content_tag else []
        if not contents:
            print("내용 불러오기 오류: <p> 태그가 없습니다.")
            content_text = "본문 없음"
        else:
            content_text = [p.text.strip() for p in contents]  # 모든 <p> 태그의 텍스트 리스트
            for text in content_text:
                print(f"{text}")
        time.sleep(1)
    except requests.RequestException as e:
        print(f"링크 불러오기 오류: {e}")
        continue

with open('kosaf_links.pkl', 'wb') as f:
    pickle.dump([link for link, _ in post_links], f)

#for page in range(1, pgSize):

# #게시물 링크
# post_links = []

# for page in rage(1,)