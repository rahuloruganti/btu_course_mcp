from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from typing import List, Optional

from bs4 import BeautifulSoup

from config import BASE_URL, DEFAULT_SEMESTER, HEADERS, SEMESTER_IDS
from models import Course, ModuleInfo, Schedule
from scrapers.parser import clean_text, get_page_title


async def fetch_page(url: str, params: dict | None = None) -> BeautifulSoup:
    async with httpx.AsyncClient(
        headers=HEADERS,
        follow_redirects=True,
        timeout=20,
    ) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        response.encoding = response.encoding or "utf-8"
    return BeautifulSoup(response.text, "html.parser")


async def search_courses(query: str, semester: str = DEFAULT_SEMESTER) -> List[Course]:
    semester_id = _resolve_semester_id(semester)
    candidates = _build_search_params(query=query, semester_id=semester_id)

    for params in candidates:
        try:
            soup = await fetch_page(BASE_URL, params=params)
            courses = _parse_course_search_results(soup, semester=semester)
            if courses:
                return courses
        except httpx.HTTPError:
            continue

    # Fallback source used by BTU faculty planning pages.
    planning_courses = await _search_courses_from_math_planning(query=query, semester=semester)
    if planning_courses:
        return planning_courses

    return []


async def get_schedule(course_id: str) -> Optional[Schedule]:
    for params in _build_course_detail_params(course_id):
        try:
            soup = await fetch_page(BASE_URL, params=params)
        except httpx.HTTPError:
            continue

        schedule = _parse_schedule_page(soup=soup, course_id=course_id)
        if schedule:
            return schedule

    return None


async def get_module_info(module_number: str) -> Optional[ModuleInfo]:
    for params in _build_module_detail_params(module_number):
        try:
            soup = await fetch_page(BASE_URL, params=params)
        except httpx.HTTPError:
            continue

        info = _parse_module_page(soup=soup, module_number=module_number, params=params)
        if info and info.name:
            return info

    return None


def _resolve_semester_id(semester: str) -> str:
    if semester in SEMESTER_IDS:
        return SEMESTER_IDS[semester]
    return semester


def _build_search_params(query: str, semester_id: str) -> list[dict[str, str]]:
    # QIS installations differ; try common search forms in order.
    return [
        {
            "state": "wsearchv",
            "search": "1",
            "subdir": "veranstaltung",
            "k_semester.semid": semester_id,
            "P.vx": query,
            "P.suche": "Suche",
        },
        {
            "state": "verpublish",
            "status": "init",
            "vmfile": "no",
            "moduleCall": "webSC",
            "publishConfFile": "webSC",
            "publishSubDir": "veranstaltung",
            "search": "true",
            "query": query,
            "k_semester.semid": semester_id,
        },
        {
            "state": "verpublish",
            "status": "init",
            "vmfile": "no",
            "moduleCall": "webSC",
            "publishConfFile": "webSC",
            "publishSubDir": "veranstaltung",
            "P.suche": "suchen",
            "P.vx": query,
            "k_semester.semid": semester_id,
        },
    ]


def _build_course_detail_params(course_id: str) -> list[dict[str, str]]:
    return [
        {
            "state": "verpublish",
            "status": "init",
            "vmfile": "no",
            "moduleCall": "webInfo",
            "publishConfFile": "webInfo",
            "publishSubDir": "veranstaltung",
            "veranstaltung.veranstid": course_id,
        },
        {
            "state": "verpublish",
            "status": "init",
            "vmfile": "no",
            "publishid": course_id,
        },
    ]


def _build_module_detail_params(module_number: str) -> list[dict[str, str]]:
    return [
        {
            "state": "verpublish",
            "status": "init",
            "vmfile": "no",
            "moduleCall": "webInfo",
            "publishConfFile": "webInfo",
            "publishSubDir": "modul",
            "modul.modulid": module_number,
        },
        {
            "state": "verpublish",
            "status": "init",
            "vmfile": "no",
            "publishid": module_number,
        },
    ]


def _parse_course_search_results(soup: BeautifulSoup, semester: str) -> list[Course]:
    courses: list[Course] = []
    seen: set[str] = set()

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue

        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 1:
                continue

            link = row.find("a", href=True)
            if not link:
                continue

            href = link.get("href", "")
            course_id = (
                _extract_param(href, "veranstaltung.veranstid")
                or _extract_param(href, "publishid")
                or _extract_param(href, "id")
                or ""
            )
            name = clean_text(link.get_text(" ", strip=True))
            if not name:
                continue

            unique_key = course_id or f"{name}:{href}"
            if unique_key in seen:
                continue
            seen.add(unique_key)

            values = [clean_text(c.get_text(" ", strip=True)) for c in cells]
            values = [v for v in values if v]

            lecturer = values[1] if len(values) > 1 else None
            course_type = values[2] if len(values) > 2 else None
            ects = _find_first_ects(values)

            courses.append(
                Course(
                    id=course_id,
                    name=name,
                    lecturer=lecturer,
                    semester=semester,
                    course_type=course_type,
                    ects=ects,
                    url=_absolute_url(href),
                )
            )

    return courses


def _parse_schedule_page(soup: BeautifulSoup, course_id: str) -> Optional[Schedule]:
    schedule_table = None
    for table in soup.find_all("table"):
        header = clean_text(table.get_text(" ", strip=True)) or ""
        if any(token in header.lower() for token in ["tag", "zeit", "raum", "rhythmus", "termine"]):
            schedule_table = table
            break

    if not schedule_table:
        return None

    data_rows = schedule_table.find_all("tr")
    first = None
    for row in data_rows:
        cols = row.find_all("td")
        if cols:
            first = cols
            break

    if not first:
        return None

    values = [clean_text(col.get_text(" ", strip=True)) for col in first]
    day = values[0] if len(values) > 0 else None
    time_val = values[1] if len(values) > 1 else None
    room = values[2] if len(values) > 2 else None
    recurrence = values[3] if len(values) > 3 else None
    time_start, time_end = _split_time_range(time_val)

    return Schedule(
        course_id=course_id,
        course_name=get_page_title(soup),
        day=day,
        time_start=time_start,
        time_end=time_end,
        room=room,
        recurrence=recurrence,
    )


def _parse_module_page(soup: BeautifulSoup, module_number: str, params: dict[str, str]) -> Optional[ModuleInfo]:
    if "login" in (soup.get_text(" ", strip=True) or "").lower():
        return None

    name = get_page_title(soup)
    if not name:
        return None

    def find_field(labels: list[str]) -> Optional[str]:
        for needle in labels:
            for tag in soup.find_all(["td", "th", "dt", "strong", "b"]):
                text = clean_text(tag.get_text(" ", strip=True)) or ""
                if needle.lower() in text.lower():
                    sibling = tag.find_next_sibling()
                    if sibling:
                        value = clean_text(sibling.get_text(" ", strip=True))
                        if value:
                            return value
                    dd = tag.find_next("dd")
                    if dd:
                        value = clean_text(dd.get_text(" ", strip=True))
                        if value:
                            return value
        return None

    return ModuleInfo(
        module_number=module_number,
        name=name,
        description=find_field(["Inhalt", "Beschreibung", "Modulbeschreibung"]),
        ects=find_field(["ECTS", "ECTS-Punkte"]),
        exam_type=find_field(["Prüfungsform", "Pruefungsform", "Prüfungsleistung"]),
        prerequisites=find_field(["Voraussetzungen", "Teilnahmevoraussetzungen"]),
        lecturer=find_field(["Dozent", "Lehrende", "Verantwortliche"]),
        url=str(httpx.URL(BASE_URL).copy_with(params=params)),
    )


def _extract_param(url: str, param_name: str) -> Optional[str]:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    values = query.get(param_name, [])
    return values[0] if values else None


def _absolute_url(href: str) -> str:
    return urljoin(BASE_URL, href)


def _split_time_range(time_val: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not time_val:
        return None, None

    normalized = time_val.replace(".", ":")
    match = re.search(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})", normalized)
    if match:
        return match.group(1), match.group(2)
    return normalized, None


def _find_first_ects(values: list[Optional[str]]) -> Optional[str]:
    for value in values:
        if not value:
            continue
        if re.search(r"\b\d+(?:[.,]\d+)?\b", value) and "ects" in value.lower():
            return value
    return None


def _extract_building_code(place: Optional[str]) -> Optional[str]:
    """Extract building code from place string like 'G9_SD/9.219'."""
    if not place:
        return None
    parts = place.split("/")
    return parts[0].strip() if parts else None


async def _search_courses_from_math_planning(query: str, semester: str) -> list[Course]:
    planning_url = _planning_semester_url(semester) or "https://www.math.b-tu.de/perl-lp/planung.cgi"
    lectures_overview_url = await _discover_lectures_overview_url(planning_url)
    if not lectures_overview_url:
        return []

    try:
        soup = await fetch_page(lectures_overview_url)
    except httpx.HTTPError:
        return []

    query_lower = (query or "").strip().lower()
    inferred_semester = _extract_semester_label(soup) or semester
    results: list[Course] = []
    seen: set[str] = set()

    h4_tags = soup.find_all("h4")
    for idx, h4 in enumerate(h4_tags):
        course_id = clean_text(h4.get_text(" ", strip=True)) or ""
        if not course_id.isdigit():
            continue

        title_tag = h4_tags[idx + 1] if idx + 1 < len(h4_tags) else None
        if not title_tag:
            continue
        name = clean_text(title_tag.get_text(" ", strip=True)) or ""
        if not name:
            continue

        study_programs = _extract_study_programs(title_tag)
        search_haystack = " ".join([course_id, name, study_programs or ""]).lower()
        if query_lower and query_lower not in search_haystack:
            continue

        course_type, lecturer, day, time_start, time_end, place = _extract_event_meta(title_tag)
        building = _extract_building_code(place) if place else None
        module_url = _extract_module_url(title_tag)

        key = f"{course_id}:{name}"
        if key in seen:
            continue
        seen.add(key)

        results.append(
            Course(
                id=course_id,
                name=name,
                lecturer=lecturer,
                semester=inferred_semester,
                course_type=course_type,
                ects=None,
                url=module_url or lectures_overview_url,
                day=day,
                time_start=time_start,
                time_end=time_end,
                place=place,
                building=building,
            )
        )

    return results


def _planning_semester_url(semester: str) -> Optional[str]:
    token = _semester_plan_token(semester)
    if not token:
        return None
    return f"https://www.math.b-tu.de/perl-lp/planung_{token}.cgi"


def _semester_plan_token(semester: str) -> Optional[str]:
    value = (semester or "").strip()

    # Supported key format from this project, e.g. SoSe2025 / WiSe2025.
    key_match = re.match(r"^(SoSe|WiSe)\s*(\d{4})$", value, flags=re.IGNORECASE)
    if key_match:
        prefix = "ss" if key_match.group(1).lower() == "sose" else "ws"
        return f"{prefix}{key_match.group(2)[-2:]}"

    # Semester IDs like 20251 and 20252, where 1=SoSe and 2=WiSe.
    semid_match = re.match(r"^(\d{4})([12])$", value)
    if semid_match:
        prefix = "ss" if semid_match.group(2) == "1" else "ws"
        return f"{prefix}{semid_match.group(1)[-2:]}"

    # Human labels like "Sommersemester 2025" or "Wintersemester 2025/2026".
    label_match = re.search(r"(Sommersemester|Wintersemester)\s+(\d{4})", value, flags=re.IGNORECASE)
    if label_match:
        prefix = "ss" if label_match.group(1).lower().startswith("sommer") else "ws"
        return f"{prefix}{label_match.group(2)[-2:]}"

    return None


async def _discover_lectures_overview_url(planning_url: str) -> Optional[str]:
    try:
        soup = await fetch_page(planning_url)
    except httpx.HTTPError:
        return None

    for link in soup.find_all("a", href=True):
        text = clean_text(link.get_text(" ", strip=True)) or ""
        href = link.get("href", "")
        if "sämtliche lehrveranstaltungen" in text.lower() or "saemtliche lehrveranstaltungen" in text.lower():
            return urljoin(planning_url, href)
        if re.search(r"/plan/(ws|ss)\d{2}/", href):
            return urljoin(planning_url, href)

    return None


def _extract_study_programs(anchor_tag: Any) -> Optional[str]:
    green = anchor_tag.find_next("font", attrs={"color": "green"})
    if not green:
        return None
    text = clean_text(green.get_text(" ", strip=True))
    if not text:
        return None
    return text.replace("Studiengänge", "").strip()


def _extract_event_meta(anchor_tag: Any) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Extract course type, lecturer, day, time, place from event table.
    
    Returns: (course_type, lecturer, day, time_start, time_end, place)
    """
    cursor = anchor_tag
    for _ in range(6):
        table = cursor.find_next("table") if cursor else None
        if not table:
            break

        header_b = table.find("b")
        header_text = clean_text(header_b.get_text(" ", strip=True)) if header_b else None
        if header_text and header_text.lower() not in {"modul", "module"}:
            rows = table.find_all("tr")
            if len(rows) < 2:
                return header_text, None, None, None, None, None
            cols = rows[1].find_all("td")
            if not cols:
                return header_text, None, None, None, None, None
            
            # Extract schedule details from first row
            day = clean_text(cols[0].get_text(" ", strip=True)) if len(cols) > 0 else None
            # cols[1] is often "AB" or other type marker
            time_str = clean_text(cols[2].get_text(" ", strip=True)) if len(cols) > 2 else None
            place = clean_text(cols[3].get_text(" ", strip=True)) if len(cols) > 3 else None
            lecturer = clean_text(cols[-1].get_text(" ", strip=True)) if cols else None
            
            time_start, time_end = _split_time_range(time_str)
            building = _extract_building_code(place) if place else None
            
            return header_text, lecturer, day, time_start, time_end, place
        
        cursor = table
    
    return None, None, None, None, None, None



def _extract_module_url(anchor_tag: Any) -> Optional[str]:
    cursor = anchor_tag
    for _ in range(4):
        table = cursor.find_next("table") if cursor else None
        if not table:
            break
        for link in table.find_all("a", href=True):
            href = link.get("href", "")
            if "/modul/" in href:
                return href
        cursor = table
    return None


def _extract_semester_label(soup: BeautifulSoup) -> Optional[str]:
    text = clean_text(soup.get_text(" ", strip=True)) or ""
    match = re.search(r"(Wintersemester|Sommersemester)\s+\d{4}/\d{4}", text, flags=re.IGNORECASE)
    if match:
        return match.group(0)
    return None
