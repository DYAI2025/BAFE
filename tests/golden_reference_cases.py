"""
Extended golden reference cases for BaZi Engine.

Each case is a tuple of:
    (id, birth_local, timezone, longitude, latitude, expected_pillars, source)

expected_pillars is a tuple of (Year, Month, Day, Hour) pillar strings,
e.g. ("JiaChen", "BingYin", "WuXu", "DingSi").

All expected values were computed by the BaZi Engine v1.0.0-rc0 using
Swiss Ephemeris and verified for structural correctness.

Sources:
- "engine"    = computed by BaZi Engine, verified structurally
- "lichun"    = LiChun boundary test (year pillar must flip)
- "zi_hour"   = Zi hour day-boundary test
- "geo"       = geographic diversity (tropical, southern hemisphere, high lat)
- "historical" = historically notable date
"""
from __future__ import annotations

from typing import Tuple

# (id, birth_local, timezone, lon, lat, (year, month, day, hour), source_note)
GoldenCase = Tuple[str, str, str, float, float, Tuple[str, str, str, str], str]

EXTENDED_GOLDEN_CASES: list[GoldenCase] = [
    # --- Historical / Notable Dates ---
    (
        "singapore_independence",
        "1965-08-09T10:00:00",
        "Asia/Singapore",
        103.85,
        1.29,
        ("YiSi", "JiaShen", "YiWei", "XinSi"),
        "historical: Singapore independence proclamation, 9 Aug 1965 10:00 SGT",
    ),
    # --- Timezone Diversity ---
    (
        "tokyo_midnight",
        "2024-01-01T00:05:00",
        "Asia/Tokyo",
        139.69,
        35.69,
        ("GuiMao", "JiaZi", "JiaZi", "JiaZi"),
        "geo: Tokyo just after midnight on New Year 2024 (JST, UTC+9)",
    ),
    (
        "sydney_summer",
        "2024-01-15T15:00:00",
        "Australia/Sydney",
        151.21,
        -33.87,
        ("GuiMao", "YiChou", "WuYin", "GengShen"),
        "geo: Sydney in southern-hemisphere summer, AEDT (UTC+11)",
    ),
    (
        "cape_town_winter",
        "2024-07-15T09:00:00",
        "Africa/Johannesburg",
        18.42,
        -33.92,
        ("JiaChen", "XinWei", "GengChen", "XinSi"),
        "geo: Cape Town in southern-hemisphere winter, SAST (UTC+2)",
    ),
    (
        "bangkok_equinox",
        "2024-03-20T12:00:00",
        "Asia/Bangkok",
        100.50,
        13.76,
        ("JiaChen", "DingMao", "GuiWei", "WuWu"),
        "geo: Bangkok near vernal equinox, tropical latitude (ICT, UTC+7)",
    ),
    # --- LiChun Boundary (Beijing) ---
    # LiChun 2024 falls at ~16:27 CST on Feb 4.
    # One minute before: year = GuiMao (2023).
    # One minute after: year = JiaChen (2024).
    (
        "lichun_2024_before_beijing",
        "2024-02-04T16:26:00",
        "Asia/Shanghai",
        116.40,
        39.90,
        ("GuiMao", "YiChou", "WuXu", "GengShen"),
        "lichun: 1 min before LiChun 2024 in Beijing — year still GuiMao",
    ),
    (
        "lichun_2024_after_beijing",
        "2024-02-04T16:28:00",
        "Asia/Shanghai",
        116.40,
        39.90,
        ("JiaChen", "BingYin", "WuXu", "GengShen"),
        "lichun: 1 min after LiChun 2024 in Beijing — year flips to JiaChen",
    ),
    # --- Zi Hour / Day Boundary ---
    # 23:30 Berlin is Zi hour (early rat), same calendar day.
    # 00:30 Berlin next day is also Zi hour but next calendar day.
    (
        "zi_hour_before_midnight",
        "2024-06-15T23:30:00",
        "Europe/Berlin",
        13.405,
        52.52,
        ("JiaChen", "GengWu", "GengXu", "BingZi"),
        "zi_hour: 23:30 Berlin — Zi hour, still Jun 15 day pillar",
    ),
    (
        "zi_hour_after_midnight",
        "2024-06-16T00:30:00",
        "Europe/Berlin",
        13.405,
        52.52,
        ("JiaChen", "GengWu", "XinHai", "WuZi"),
        "zi_hour: 00:30 Berlin — Zi hour, Jun 16 day pillar (next day)",
    ),
    # --- High Latitude ---
    (
        "reykjavik_summer_solstice",
        "2024-06-21T12:00:00",
        "Atlantic/Reykjavik",
        -21.9,
        64.15,
        ("JiaChen", "GengWu", "BingChen", "JiaWu"),
        "geo: Reykjavik at summer solstice, high latitude 64N (GMT, UTC+0)",
    ),
    # --- Tropical ---
    (
        "mumbai_monsoon",
        "2024-07-01T06:00:00",
        "Asia/Kolkata",
        72.88,
        19.08,
        ("JiaChen", "GengWu", "BingYin", "XinMao"),
        "geo: Mumbai early monsoon season, IST (UTC+5:30)",
    ),
    # --- South America ---
    (
        "sao_paulo_new_year",
        "2024-01-01T00:01:00",
        "America/Sao_Paulo",
        -46.63,
        -23.55,
        ("GuiMao", "JiaZi", "JiaZi", "JiaZi"),
        "geo: São Paulo just after midnight on New Year, BRT (UTC-3)",
    ),
]
