"""Tests for HTML parsing of external fetchers."""

from datetime import date

from lotto.fetchers.five_hundred import parse_history_html
from lotto.normalize import Draw, normalise_draws


SAMPLE_HTML = """
<table id="tablelist">
  <tr>
    <td class="td1">2024002</td>
    <td class="td2">2024-01-04</td>
    <td class="ball_red">01</td>
    <td class="ball_red">07</td>
    <td class="ball_red">08</td>
    <td class="ball_red">14</td>
    <td class="ball_red">19</td>
    <td class="ball_red">30</td>
    <td class="ball_blue">12</td>
  </tr>
  <tr>
    <td class="td1">2024001</td>
    <td class="td2">2024-01-02</td>
    <td class="ball_red">02</td>
    <td class="ball_red">05</td>
    <td class="ball_red">11</td>
    <td class="ball_red">24</td>
    <td class="ball_red">28</td>
    <td class="ball_red">33</td>
    <td class="ball_blue">09</td>
  </tr>
</table>
"""


def test_parse_history_html_returns_draws_in_chronological_order():
    draws = parse_history_html(SAMPLE_HTML)
    assert len(draws) == 2
    assert isinstance(draws[0], Draw)
    assert draws[0].issue == "2024001"
    assert draws[0].date == date(2024, 1, 2)
    assert draws[0].reds == [2, 5, 11, 24, 28, 33]
    assert draws[0].blue == 9


def test_normalised_dataframe_structure():
    draws = parse_history_html(SAMPLE_HTML)
    frame = normalise_draws(draws)
    assert list(frame.columns) == [
        "date",
        "issue",
        "red1",
        "red2",
        "red3",
        "red4",
        "red5",
        "red6",
        "blue",
    ]
    assert len(frame) == 2
    assert frame.iloc[1]["blue"] == 12
