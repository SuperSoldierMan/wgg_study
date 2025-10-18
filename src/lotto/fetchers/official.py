"""Fetcher for lottery data from the official China Welfare Lottery website."""

from __future__ import annotations

import math
import re
import time
from datetime import date, timedelta
from typing import Dict, List, Optional

import requests

from ..exceptions import FetchError
from ..normalize import Draw, parse_date

BASE_URL = "https://www.cwl.gov.cn/cwl_admin/kjxx/findDrawNotice"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36"
    ),
    "Origin": "https://www.cwl.gov.cn",
    "Referer": "https://www.cwl.gov.cn/",
}
PAGE_SIZE = 30
MAX_PAGES = 400


def fetch_draws(
    years: int = 15,
    session: Optional[requests.Session] = None,
    sleep: float = 0.4,
    max_retries: int = 3,
) -> List[Draw]:
    """Fetch draw information from the official Welfare Lottery endpoint."""

    session = session or requests.Session()
    cutoff = date.today() - timedelta(days=int(math.ceil(years * 365.25)))
    draws: List[Draw] = []
    seen_issues: Dict[str, Draw] = {}

    for page in range(1, MAX_PAGES + 1):
        payload = {
            "name": "ssq",
            "issueCount": "",
            "issueStart": "",
            "issueEnd": "",
            "dayStart": "",
            "dayEnd": "",
            "pageNo": page,
            "pageSize": PAGE_SIZE,
        }
        for attempt in range(1, max_retries + 1):
            try:
                response = session.post(BASE_URL, data=payload, headers=HEADERS, timeout=15)
                response.raise_for_status()
                data = response.json()
                break
            except (requests.RequestException, ValueError) as exc:
                if attempt == max_retries:
                    raise FetchError(f"Failed to fetch page {page} from official source: {exc}") from exc
                time.sleep(sleep * attempt)
        else:  # pragma: no cover - unreachable thanks to raise above
            continue

        records = _extract_records(data)
        if not records:
            break

        page_exhausted = False
        for record in records:
            issue_str = str(
                record.get("code")
                or record.get("issue")
                or record.get("lotteryDrawNum")
                or ""
            ).strip()
            if not issue_str:
                continue
            date_value = (
                record.get("date")
                or record.get("awardDateTime")
                or record.get("lotteryDrawTime")
            )
            red_values = (
                record.get("red")
                or record.get("redBall")
                or record.get("lotteryDrawResult")
                or record.get("drawRedBall")
                or ""
            )
            blue_value = (
                record.get("blue")
                or record.get("blueBall")
                or record.get("drawBlueBall")
                or ""
            )
            if not date_value or not red_values or not blue_value:
                continue
            try:
                draw_date = parse_date(str(date_value))
            except Exception:
                continue
            red_matches = [int(value) for value in re.findall(r"\d{1,2}", str(red_values))]
            if len(red_matches) < 6:
                continue
            blue_matches = [int(value) for value in re.findall(r"\d{1,2}", str(blue_value))]
            if not blue_matches:
                continue
            reds = red_matches[:6]
            blue = blue_matches[0]

            draw = Draw(date=draw_date, issue=issue_str, reds=reds, blue=blue)
            seen_issues[issue_str] = draw
            if cutoff and draw_date < cutoff:
                page_exhausted = True
        if page_exhausted:
            break
        time.sleep(sleep)

    draws = sorted(seen_issues.values(), key=lambda d: (d.date, d.issue))
    if cutoff:
        draws = [draw for draw in draws if draw.date >= cutoff]
    if not draws:
        raise FetchError("No draws collected from official source.")
    return draws


def _extract_records(data: dict) -> List[dict]:
    if not isinstance(data, dict):
        return []
    if "result" in data and isinstance(data["result"], dict):
        result = data["result"]
        if isinstance(result, dict) and "data" in result and isinstance(result["data"], list):
            return result["data"]
        if isinstance(result, dict) and "list" in result and isinstance(result["list"], list):
            return result["list"]
    if "data" in data and isinstance(data["data"], dict):
        inner = data["data"]
        if "list" in inner and isinstance(inner["list"], list):
            return inner["list"]
        if "data" in inner and isinstance(inner["data"], list):
            return inner["data"]
    if "list" in data and isinstance(data["list"], list):
        return data["list"]
    if "result" in data and isinstance(data["result"], list):
        return data["result"]
    return []
