import os
import requests
from datetime import datetime, timezone, timedelta

MMT = timezone(timedelta(hours=6, minutes=30))

FDO_KEY = os.environ["FOOTBALL_DATA_API_KEY"]
ODDS_KEY = os.environ["ODDS_API_KEY"]
GEMINI_KEY = os.environ["GEMINI_API_KEY"]

GEMINI_MODEL = "gemini-3.6-flash"

COMPETITIONS = {
    "PL": "EPL",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "CL": "UCL",
}

MYANMAR_ODDS = {
    0.0: "D",
    0.25: "L-50",
    0.5: "L-100",
    0.75: "1+50",
    1.0: "1D",
    1.25: "1-50",
    1.5: "1-100",
    1.75: "2+50",
    2.0: "2D",
    2.25: "2-50",
    2.5: "2-100",
    2.75: "3+50",
    3.0: "3D",
    3.25: "3-50",
    3.5: "3-100",
    3.75: "4+50",
    4.0: "4D",
}


def asian_to_myanmar(line):
    if line is None:
        return None

    line = abs(float(line))

    for key, value in MYANMAR_ODDS.items():
        if abs(key - line) < 0.001:
            return value

    return None


def get_one_fdo_match():
    now = datetime.now(MMT)
    today = now.date()

    from_date = today.strftime("%Y-%m-%d")
    to_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")

    url = "https://api.football-data.org/v4/matches"

    headers = {
        "X-Auth-Token": FDO_KEY
    }

    params = {
        "competitions": ",".join(COMPETITIONS.keys()),
        "dateFrom": from_date,
        "dateTo": to_date,
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    print("FDO HTTP:", response.status_code)
    print("FDO DATE RANGE:", from_date, "to", to_date)

    response.raise_for_status()

    data = response.json()
    matches = data.get("matches", [])

    print("FDO MATCH COUNT:", len(matches))

    candidates = []

    for match in matches:
        competition = match.get("competition", {})
        code = competition.get("code")

        if code not in COMPETITIONS:
            continue

        utc_date = match.get("utcDate")

        if not utc_date:
            continue

        match_mmt = datetime.fromisoformat(
            utc_date.replace("Z", "+00:00")
        ).astimezone(MMT)

        print(
            "FDO MATCH RAW:",
            competition.get("name"),
            "|",
            match.get("homeTeam", {}).get("name"),
            "vs",
            match.get("awayTeam", {}).get("name"),
            "|",
            match_mmt.strftime("%Y-%m-%d %H:%M"),
        )

    if match_mmt <= now:
            continue

        candidates.append((match_mmt, match))

    if not candidates:
        raise RuntimeError(
    "FDO returned matches, but no future match remains in the next 7 days."
)

    candidates.sort(key=lambda x: x[0])

    return candidates[0][1]


def normalize_name(name):
    if not name:
        return ""

    return (
        name.lower()
        .replace("fc", "")
        .replace("afc", "")
        .replace("cf", "")
        .replace("  ", " ")
        .strip()
    )


def get_odds_match(home, away):
    url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"

    params = {
        "apiKey": ODDS_KEY,
        "regions": "eu",
        "markets": "spreads,totals",
        "oddsFormat": "decimal",
    }

    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    print("ODDS HTTP:", response.status_code)

    response.raise_for_status()

    events = response.json()

    home_n = normalize_name(home)
    away_n = normalize_name(away)

    for event in events:
        event_home = normalize_name(event.get("home_team"))
        event_away = normalize_name(event.get("away_team"))

        if event_home == home_n and event_away == away_n:
            return event

    return None


def choose_line(event):
    preferred_totals = [2.25, 2.5, 2.75, 3.0]
    preferred_handicaps = [-0.25, -0.5, -0.75, -1.0]

    if not event:
        return None

    for bookmaker in event.get("bookmakers", []):
        for market in bookmaker.get("markets", []):

            if market.get("key") == "totals":
                outcomes = market.get("outcomes", [])

                for line in preferred_totals:
                    for outcome in outcomes:
                        point = outcome.get("point")

                        if point is not None and abs(point - line) < 0.001:
                            return {
                                "market": "O/U",
                                "line": line,
                                "myanmar_odds": asian_to_myanmar(line),
                            }

            if market.get("key") == "spreads":
                outcomes = market.get("outcomes", [])

                for line in preferred_handicaps:
                    for outcome in outcomes:
                        point = outcome.get("point")

                        if point is not None and abs(point - abs(line)) < 0.001:
                            return {
                                "market": "AH",
                                "line": line,
                                "myanmar_odds": asian_to_myanmar(line),
                            }

    return None


def call_gemini(home, away, competition, market, line, myanmar_odds):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
    )

    prompt = f"""
You are a football analysis assistant.

Competition: {competition}
Home: {home}
Away: {away}
Market: {market}
Asian Line: {line}
Myanmar Odds: {myanmar_odds}

Allowed competitions only:
EPL, La Liga, Serie A, Bundesliga, Ligue 1, UCL.

Rules:
- Do not invent injuries, lineups, news, statistics, odds or evidence.
- If reliable evidence is insufficient, return PASS.
- Do not change the supplied competition, teams, market, line or Myanmar odds.
- Historical BT is only supporting evidence, not a guarantee.
- Output JSON only.

Return exactly:

{{
  "status": "PICK or PASS",
  "strength": "Strong, Good, Moderate, or PASS",
  "reason": "short factual reason",
  "competition": "{competition}",
  "home": "{home}",
  "away": "{away}",
  "market": "{market}",
  "asian_line": {line},
  "myanmar_odds": "{myanmar_odds}"
}}
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_KEY,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=60,
    )

    print("GEMINI HTTP:", response.status_code)

    response.raise_for_status()

    data = response.json()

    text = (
        data["candidates"][0]["content"]["parts"][0]["text"]
        .strip()
    )

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    import json

    result = json.loads(text)

    # Lock critical fields
    result["competition"] = competition
    result["home"] = home
    result["away"] = away
    result["market"] = market
    result["asian_line"] = line
    result["myanmar_odds"] = myanmar_odds

    return result


def main():
    print("=" * 50)
    print("ANALYSIS FOOTBALL INTEGRATION TEST")
    print("=" * 50)

    match = get_one_fdo_match()

    competition_code = match["competition"]["code"]
    competition = COMPETITIONS[competition_code]

    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]

    print()
    print("SELECTED MATCH:")
    print(competition)
    print(home, "vs", away)

    odds_event = get_odds_match(home, away)

    if not odds_event:
        raise RuntimeError(
            "No matching Odds API event found for selected match."
        )

    line_info = choose_line(odds_event)

    if not line_info:
        raise RuntimeError(
            "No supported Asian line found."
        )

    print()
    print("SELECTED MARKET:")
    print(line_info)

    result = call_gemini(
        home=home,
        away=away,
        competition=competition,
        market=line_info["market"],
        line=line_info["line"],
        myanmar_odds=line_info["myanmar_odds"],
    )

    print()
    print("GEMINI RESULT:")
    print(result)

    print()
    print("=" * 50)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()
