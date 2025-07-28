from typing import Optional, List, Dict, Any, Set

from models.scholarship_region import ScholarshipRegion

from .address_parser import address_parser

def extract_region_links(
    scholarship_id: int,
    raw_text: Optional[str],
    org_text: Optional[str],
    sido_map: Dict[str, int],
    all_sigungus_map: Dict[str, List[Dict[str, int]]],
    all_eupmyeondongs_map: Dict[str, List[Dict[str, Any]]],
    id_to_region_map: Dict[str, Any]
) -> List[ScholarshipRegion]:
    """
    재귀(Recursion) 방식으로, 문맥이 충분할 땐 부모까지 함께,
    그렇지 않을 땐 해당 자식 지역 ID만이라도 저장하도록 개선한 버전
    """
    if not raw_text:
        return []

    parsed_region_names = address_parser(text=raw_text, org_name=org_text)
    if not parsed_region_names:
        return []

    links: List[ScholarshipRegion] = []
    found_ids: Set[int] = set()

    def add_with_parents_recursive(region_id: Optional[int]):
        if region_id is None or region_id in found_ids:
            return
        found_ids.add(region_id)
        links.append(ScholarshipRegion(scholarship_id=scholarship_id, region_id=region_id))

        region_info = id_to_region_map.get(str(region_id))
        if region_info:
            add_with_parents_recursive(region_info.get('parent_id'))

    # 텍스트 내 시/도·시/군/구 이름
    sidos_in_text    = {n for n in parsed_region_names if n in sido_map}
    sigungus_in_text = {n for n in parsed_region_names if n in all_sigungus_map}

    # 1. 읍/면/동 처리
    for name in parsed_region_names:
        if name in all_eupmyeondongs_map:
            matches = all_eupmyeondongs_map[name]
            match_to_add = None

            if len(matches) == 1:
                match_to_add = matches[0]
            else:
                # 문맥으로 명확히 하나만 골라낼 수 있는 경우
                for m in matches:
                    if (m.get('sido') in sidos_in_text and
                        m.get('sigungu') in sigungus_in_text):
                        match_to_add = m
                        break

            if match_to_add:
                # 문맥 충분 → 부모까지 모두 추가
                add_with_parents_recursive(match_to_add['id'])
            else:
                # 문맥 불충분 & 다중 매칭 → 자식 지역 ID만이라도 추가
                for m in matches:
                    rid = m['id']
                    if rid not in found_ids:
                        found_ids.add(rid)
                        links.append(ScholarshipRegion(scholarship_id=scholarship_id, region_id=rid))

    # 2. 시/군/구 처리
    for name in parsed_region_names:
        if name in all_sigungus_map:
            matches = all_sigungus_map[name]
            match_to_add = None

            if len(matches) == 1:
                match_to_add = matches[0]
            else:
                sido_ids = {sido_map[s] for s in sidos_in_text}
                for m in matches:
                    if m.get('parent_id') in sido_ids:
                        match_to_add = m
                        break

            if match_to_add:
                add_with_parents_recursive(match_to_add['id'])
            else:
                # 문맥 불충분 & 다중 매칭 → 자식 지역 ID만이라도 추가
                for m in matches:
                    rid = m['id']
                    if rid not in found_ids:
                        found_ids.add(rid)
                        links.append(ScholarshipRegion(scholarship_id=scholarship_id, region_id=rid))

    # 3. 시/도 처리
    for name in parsed_region_names:
        if name in sido_map:
            add_with_parents_recursive(sido_map[name])

    return links