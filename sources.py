# Analysis Football Bot — Verified Data Sources
# Primary: Football-Data.org (FDO)
# Backup sources are intentionally not enabled until verified.

import os
import requests
from datetime import datetime, timezone, timedelta

FDO_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

MMT = timezone(timedelta(hours=6, minutes=30))

COMPETITIONS = {
    "PL": "EPL",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "CL": "UCL",
}

FDO_URL = "https://api.football-data.org/v4/matches"


def _mmt_day_utc_range(day):
    start_mmt = datetime.combine(
        day, datetime.min.time(), tzinfo=MMT
    )
    end_mmt = start_mmt + timedelta(days=1)

    return (
        start_mmt.astimezone(timezone.utc).strftime("%Y-%m-%d"),
        end_mmt.astimezone(timezone.utc).strftime("%Y-%m-%d"),
    )


def get_verified_matches(day=None):
    """Return only FDO-verified matches belonging to the requested MMT day."""
    if not FDO_API_KEY:
        raise RuntimeError("FOOTBALL_DATA_API_KEY is missing")

    if day is None:
        day = datetime.now(MMT).date()

    date_from, date_to = _mmt_day_utc_range(day)

    headers = {
        "X-Auth-Token": FDO_API_KEY,
        "Accept": "application/json",
    }

    params = {
        "competitions": ",".join(COMPETITIONS),
        "dateFrom": date_from,
        "dateTo": date_to,
    }

    response = requests.get(
        FDO_URL,
        headers=headers,
        params=params,
        timeout=30,
    )

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            f"FDO returned invalid JSON: {response.text[:500]}"
        )

    if response.status_code != 200:
        raise RuntimeError(f"FDO API ERROR: {data}")

    if data.get("error"):
        raise RuntimeError(f"FDO API ERROR: {data['error']}")

    matches = data.get("matches")
    if matches is None:
        raise RuntimeError("FDO response has no matches field")

    verified = []

    for match in matches:
        competition = match.get("competition", {})
        code = competition.get("code")

        if code not in COMPETITIONS:
            continue

        home = match.get("homeTeam", {}).get("name")
        away = match.get("awayTeam", {}).get("name")
        utc_date = match.get("utcDate")
        status = match.get("status")

        if not home or not away or not utc_date:
            continue

        try:
            match_dt = datetime.fromisoformat(
                utc_date.replace("Z", "+00:00")
            )
        except ValueError:
            continue

        match_mmt = match_dt.astimezone(MMT)

        if match_mmt.date() != day:
            continue

        verified.append({
            "id": match.get("id"),
            "competition_code": code,
            "competition": COMPETITIONS[code],
            "home": home,
            "away": away,
            "utc_date": utc_date,
            "mmt_date": match_mmt.strftime("%Y-%m-%d"),
            "mmt_time": match_mmt.strftime("%I:%M %p"),
            "status": status,
        })

    verified.sort(key=lambda x: x["utc_date"])
    return verified
