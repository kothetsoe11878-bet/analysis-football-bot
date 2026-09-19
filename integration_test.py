import os
import json
import requests
from datetime import datetime, timezone, timedelta

MMT = timezone(timedelta(hours=6, minutes=30))

FDO_KEY = os.environ["FOOTBALL_DATA_API_KEY"]
ODDS_KEY = os.environ["ODDS_API_KEY"]
GEMINI_KEY = os.environ["GEMINI_API_KEY"]

GEMINI_MODEL = "gemini-3.6-flash"

COMPETITIONS = {
    "PL": ("EPL", "soccer_epl"),
    "PD": ("La Liga", "soccer_spain_la_liga"),
    "SA": ("Serie A", "soccer_italy_serie_a"),
    "BL1": ("Bundesliga", "soccer_germany_bundesliga"),
    "FL1": ("Ligue 1", "soccer_france_ligue_one"),
    "CL": ("UCL", "soccer_uefa_champs_league"),
}

MYANMAR_ODDS = {
    0.00: "D",
    0.25: "L-50",
    0.50: "L-100",
    0.75: "1+50",
    1.00: "1D",
    1.25: "1-50",
    1.50: "1-100",
    1.75: "2+50",
    2.00: "2D",
    2.25: "2-50",
    2.50: "2-100",
    2.75: "3+50",
    3.00: "3D",
    3.25: "3-50",
    3.50: "3-100",
    3.75: "4+50",
    4.00: "4D",
}


def myanmar_odds(line):
    line = abs(float(line))

    for key, value in MYANMAR_ODDS.items():
        if abs(key - line) < 0.001:
            return value

    return None


def normalize_name(name):
    if not name:
        return ""

    text = name.lower()

    for word in ["football club", "fc", "afc", "cf", "club"]:
        text = text.replace(word, "")

    return " ".join(text.split())


def get_fdo_matches():
    now = datetime.now(MMT)

    date_from = now.date().strftime("%Y-%m-%d")
    date_to = (now.date() + timedelta(days=7)).strftime("%Y-%m-%d")

    url = "https://api.football-data.org/v4/matches"

    response = requests.get(
        url,
        headers={"X-Auth-Token": FDO_KEY},
        params={
            "competitions": ",".join(COMPETITIONS.keys()),
            "dateFrom": date_from,
            "dateTo": date_to,
        },
        timeout=30,
    )

    print("FDO HTTP:", response.status_code)
    print("FDO RANGE:", date_from, "to", date_to)

    response.raise_for_status()

    matches = response.json().get("matches", [])

    print("FDO MATCH COUNT:", len(matches))

    future = []

    for match in matches:
        code = match.get("competition", {}).get("code")

        if code not in COMPETITIONS:
            continue

        utc_date = match.get("utcDate")

        if not utc_date:
            continue

        match_time = datetime.fromisoformat(
            utc_date.replace("Z", "+00:00")
        ).astimezone(MMT)

        if match_time <= now:
            continue

        future.append((match_time, match))

    future.sort(key=lambda x: x[0])

    if not future:
        raise RuntimeError(
            "FDO returned matches, but no future match exists in the next 7 days."
        )

    return future


def get_odds_events(sport_key):
    url = (
        f"https://api.the-odds-api.com/v4/sports/"
        f"{sport_key}/odds"
    )

    response = requests.get(
        url,
        params={
            "apiKey": ODDS_KEY,
            "regions": "eu",
            "markets": "totals,spreads",
            "oddsFormat": "decimal",
        },
        timeout=30,
    )

    print("ODDS HTTP:", response.status_code)

    response.raise_for_status()

    return response.json()


def find_matching_event(events, home, away):
    home_n = normalize_name(home)
    away_n = normalize_name(away)

    for event in events:
        event_home = normalize_name(event.get("home_team"))
        event_away = normalize_name(event.get("away_team"))

        if event_home == home_n and event_away == away_n:
            return event

    return None


def get_current_ou_line(event):
    points = []

    for bookmaker in event.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market.get("key") != "totals":
                continue

            for outcome in market.get("outcomes", []):
                point = outcome.get("point")

                if point is not None:
                    points.append(float(point))

    if not points:
        return None

    # Consensus current market line:
    # choose the most frequent bookmaker point.
    counts = {}

    for point in points:
        key = round(point, 2)
        counts[key] = counts.get(key, 0) + 1

    line = sorted(
        counts.items(),
        key=lambda item: (-item[1], item[0])
    )[0][0]

    return line


def call_gemini(home, away, competition, line, odds):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
    )

    prompt = f"""
You are only performing an integration test.

Competition: {competition}
Home: {home}
Away: {away}
Market: O/U
Current Asian O/U line: {line}
Myanmar odds: {odds}

Rules:
- Do not invent football facts.
- Do not invent injuries, lineups, news, statistics or BT data.
- Do not change the supplied line.
- Do not change the supplied Myanmar odds.
- If there is not enough evidence for a real prediction, return PASS.
- JSON only.

Return:
{{
  "status": "PASS",
  "competition": "{competition}",
  "home": "{home}",
  "away": "{away}",
  "market": "O/U",
  "asian_line": {line},
  "myanmar_odds": "{odds}"
}}
"""

    response = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_KEY,
        },
        json={
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        },
        timeout=60,
    )

    print("GEMINI HTTP:", response.status_code)

    response.raise_for_status()

    data = response.json()

    text = (
        data["candidates"][0]
        ["content"]["parts"][0]["text"]
        .strip()
    )

    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    return json.loads(text)


def main():
    print("=" * 60)
    print("ANALYSIS FOOTBALL INTEGRATION TEST V2")
    print("=" * 60)

    matches = get_fdo_matches()

    selected = None
    odds_event = None

    # Try future matches until one has a matching current Odds API event.
    for match_time, match in matches[:8]:
        code = match["competition"]["code"]

        competition, sport_key = COMPETITIONS[code]

        home = match["homeTeam"]["name"]
        away = match["awayTeam"]["name"]

        print()
        print("CHECK:", competition)
        print(home, "vs", away)
        print(
            "MMT:",
            match_time.strftime("%Y-%m-%d %H:%M")
        )

        events = get_odds_events(sport_key)

        event = find_matching_event(
            events,
            home,
            away,
        )

        if event:
            selected = (
                match_time,
                match,
                competition,
                sport_key,
            )
            odds_event = event
            break

    if not selected:
        raise RuntimeError(
            "FDO match found, but no matching current Odds API event "
            "was found in the first 8 future matches."
        )

    match_time, match, competition, sport_key = selected

    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]

    line = get_current_ou_line(odds_event)

    if line is None:
        raise RuntimeError(
            "Odds API event found, but no current O/U total line was found."
        )

    odds = myanmar_odds(line)

    if odds is None:
        raise RuntimeError(
            f"Current O/U line {line} has no supported Myanmar odds mapping."
        )

    print()
    print("=" * 60)
    print("SELECTED MATCH")
    print("=" * 60)
    print("Competition:", competition)
    print("Match:", home, "vs", away)
    print(
        "MMT:",
        match_time.strftime("%Y-%m-%d %H:%M")
    )

    print()
    print("CURRENT MARKET")
    print("Asian O/U:", line)
    print("Myanmar:", odds)

    result = call_gemini(
        home=home,
        away=away,
        competition=competition,
        line=line,
        odds=odds,
    )

    # Critical lock verification.
    if result.get("asian_line") != line:
        raise RuntimeError(
            "Gemini changed the supplied Asian O/U line."
        )

    if result.get("myanmar_odds") != odds:
        raise RuntimeError(
            "Gemini changed the supplied Myanmar odds."
        )

    print()
    print("GEMINI RESULT")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print()
    print("=" * 60)
    print("INTEGRATION TEST V2 PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
