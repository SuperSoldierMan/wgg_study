"""Fetcher for lottery data from 500.com history archives."""

from __future__ import annotations

import math
import time
from collections.abc import Iterable
from datetime import date, timedelta
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from ..exceptions import FetchError
from ..normalize import Draw, parse_date

BASE_URL = "https://datachart.500.com/ssq/history/newinc/history.php"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0 Safari/537.36"
    )
}


def fetch_draws(
    years: int = 15,
    session: Optional[requests.Session] = None,
    sleep: float = 0.5,
    max_retries: int = 3,
) -> List[Draw]:
    """Fetch draws from 500.com within the requested time window."""

    session = session or requests.Session()
    params = {"start": "00001", "end": "99999"}
    cutoff = date.today() - timedelta(days=int(math.ceil(years * 365.25)))

    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
            if response.status_code != 200:
                raise FetchError(f"Unexpected status code: {response.status_code}")
            if response.encoding is None or response.encoding.lower() == "iso-8859-1":
                response.encoding = "gbk"
            draws = parse_history_html(response.text, cutoff=cutoff)
            if not draws:
                raise FetchError("No draws parsed from response.")
            return draws
        except (requests.RequestException, FetchError) as exc:
            if attempt == max_retries:
                raise FetchError(f"Failed to fetch data from 500.com: {exc}") from exc
            time.sleep(sleep * attempt)
    raise FetchError("Failed to fetch data from 500.com after retries.")


def parse_history_html(
    html: str,
    cutoff: Optional[date] = None,
    limit: Optional[int] = None,
) -> List[Draw]:
    """Parse historic draw data from the 500.com HTML archive."""

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="tablelist")
    if table is None:
        raise FetchError("Could not find history table in 500.com response.")

    draws: List[Draw] = []
    rows = table.find_all("tr")
    for row in rows:
        red_cells = row.select("td.ball_red")
        blue_cell = row.select_one("td.ball_blue")
        if len(red_cells) < 6 or blue_cell is None:
            continue
        reds = [int(cell.get_text(strip=True)) for cell in red_cells[:6]]
        blue = int(blue_cell.get_text(strip=True))

        # Extract issue and date from non-ball cells
        info_values: List[str] = []
        for cell in row.find_all("td"):
            classes = cell.get("class", [])
            if any(cls.startswith("ball_") for cls in classes):
                continue
            text = cell.get_text(strip=True)
            if text:
                info_values.append(text)
            if len(info_values) >= 2:
                break
        if len(info_values) < 2:
            continue
        issue, date_text = info_values[0], info_values[1]
        if not issue.isdigit():
            continue

        draw_date = parse_date(date_text)
        if cutoff and draw_date < cutoff:
            # Rows are in reverse chronological order; stop reading once before cutoff
            break

        draw = Draw(date=draw_date, issue=issue, reds=reds, blue=blue)
        draws.append(draw)
        if limit and len(draws) >= limit:
            break

    return list(reversed(draws))
