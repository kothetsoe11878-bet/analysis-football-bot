import os
import requests
from datetime import datetime, timezone, timedelta

# ============================================================
# CONFIG
# ============================================================

MMT = timezone(timedelta(hours=6, minutes=30))

FDO_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-3.6-flash"

COMPETITIONS = {
    "PL": "EPL",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "CL": "UCL",
}

# LOCKED Myanmar Odds Mapping
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
    4.25: "4-50",
    4.50: "4-100",
    5.00: "5D",
}


def asian_to_myanmar(line):
    try:
        line = round(float(line), 2)
    except (TypeError, ValueError):
        return None

    return MYANMAR_ODDS.get(line)


# ============================================================
# 1. GET ONE UPCOMING MATCH FROM FDO
# ============================================================

def get_one_fdo_match():

    if not FDO_API_KEY:
        raise RuntimeError("FOOTBALL_DATA_API_KEY is missing")

    now = datetime.now(MMT)
    today = now.date()

    # Query today's date directly.
    date_str = today.strftime("%Y-%m-%d")

    url = "https://api.football-data.org/v4/matches"

    headers = {
        "X-Auth-Token": FDO_API_KEY,
        "Accept": "application/json",
    }

    params = {
        "competitions": ",".join(COMPETITIONS.keys()),
        "dateFrom": date_str,
        "dateTo": date_str,
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    print("FDO HTTP:", response.status_code)
    print("FDO DATE:", date_str)

    if response.status_code != 200:
        raise RuntimeError(
            f"FDO ERROR: {response.text}"
        )

    data = response.json()

    candidates = []

    for match in data.get("matches", []):

        competition = match.get("competition", {})
        code = competition.get("code")

        if code not in COMPETITIONS:
            continue

        home = match.get("homeTeam", {}).get("name")
        away = match.get("awayTeam", {}).get("name")
        utc_date = match.get("utcDate")

        if not home or not away or not utc_date:
            continue

        try:
            match_dt = datetime.fromisoformat(
                utc_date.replace("Z", "+00:00")
            )
        except ValueError:
            continue

        match_mmt = match_dt.astimezone(MMT)

        # Only today's matches in Myanmar time
        if match_mmt.date() != today:
            continue

        # Only matches that have not started
        if match_mmt <= now:
            continue

        candidates.append({
            "id": match.get("id"),
            "league": COMPETITIONS[code],
            "home": home,
            "away": away,
            "utc_date": utc_date,
            "mmt_time": match_mmt.strftime(
                "%I:%M %p"
            ),
            "mmt_datetime": match_mmt,
        })

    candidates.sort(
        key=lambda x: x["mmt_datetime"]
    )

    if not candidates:
        raise RuntimeError(
            "FDO returned today's matches, "
            "but no future match remains in MMT."
        )

    return candidates[0]


# ============================================================
# 2. GET CURRENT ODDS FROM ODDS API
# ============================================================

def get_odds_events():

    if not ODDS_API_KEY:
        raise RuntimeError("ODDS_API_KEY is missing")

    url = (
        "https://api.the-odds-api.com/v4/sports/"
        "soccer_epl/odds"
    )

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "spreads,totals",
        "oddsFormat": "decimal",
    }

    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    print("ODDS API HTTP:", response.status_code)

    if response.status_code != 200:
        raise RuntimeError(
            f"ODDS API ERROR: {response.text}"
        )

    data = response.json()

    print("Odds events:", len(data))

    return data


# ============================================================
# 3. FIND MATCH IN ODDS DATA
# ============================================================

def normalize_name(name):
    if not name:
        return ""

    return (
        name.lower()
        .replace("fc", "")
        .replace("cf", "")
        .replace("afc", "")
        .replace(".", "")
        .strip()
    )


def find_odds_match(fdo_match, odds_events):

    home = normalize_name(fdo_match["home"])
    away = normalize_name(fdo_match["away"])

    for event in odds_events:

        odds_home = normalize_name(
            event.get("home_team")
        )

        odds_away = normalize_name(
            event.get("away_team")
        )

        if (
            home in odds_home
            or odds_home in home
        ) and (
            away in odds_away
            or odds_away in away
        ):
            return event

    return None


# ============================================================
# 4. EXTRACT AVAILABLE LINES
# ============================================================

def extract_market_lines(event):

    spreads = []
    totals = []

    for bookmaker in event.get("bookmakers", []):

        for market in bookmaker.get("markets", []):

            market_key = market.get("key")

            if market_key == "spreads":

                for outcome in market.get("outcomes", []):

                    point = outcome.get("point")

                    if point is not None:
                        spreads.append({
                            "bookmaker": bookmaker.get("title"),
                            "team": outcome.get("name"),
                            "line": float(point),
                            "price": outcome.get("price"),
                        })

            elif market_key == "totals":

                for outcome in market.get("outcomes", []):

                    point = outcome.get("point")

                    if point is not None:
                        totals.append({
                            "bookmaker": bookmaker.get("title"),
                            "name": outcome.get("name"),
                            "line": float(point),
                            "price": outcome.get("price"),
                        })

    return spreads, totals


# ============================================================
# 5. SELECT ONE VERIFIED BETTING LINE
# ============================================================

def choose_line(spreads, totals):

    wanted_ah = [-0.25, -0.50, -0.75, -1.00]
    wanted_ou = [2.25, 2.50, 2.75, 3.00]

    # Prefer O/U 2.5 for the first integration test
    for item in totals:

        line = round(item["line"], 2)

        if line in wanted_ou:

            myanmar = asian_to_myanmar(line)

            if myanmar:
                return {
                    "market": "O/U",
                    "line": line,
                    "myanmar_odds": myanmar,
                    "bookmaker": item["bookmaker"],
                    "side": item["name"],
                    "price": item["price"],
                }

    # If O/U unavailable, try AH
    for item in spreads:

        line = round(item["line"], 2)

        if line in wanted_ah:

            # Myanmar mapping uses absolute line
            myanmar = asian_to_myanmar(abs(line))

            if myanmar:
                return {
                    "market": "AH",
                    "line": line,
                    "myanmar_odds": myanmar,
                    "bookmaker": item["bookmaker"],
                    "side": item["team"],
                    "price": item["price"],
                }

    return None


# ============================================================
# 6. GEMINI — ONE REQUEST ONLY
# ============================================================

def ask_gemini(match, bet):

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing")

    url = (
        f"https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
    )

    prompt = f"""
You are a football analysis assistant.

Analyze ONLY the verified information below.

Competition: {match['league']}
Home: {match['home']}
Away: {match['away']}

Market: {bet['market']}
Asian Line: {bet['line']}
Myanmar Odds: {bet['myanmar_odds']}
Bookmaker: {bet['bookmaker']}
Side: {bet['side']}
Decimal Price: {bet['price']}

IMPORTANT RULES:
1. Do not invent injuries, lineups, form, statistics or news.
2. Do not invent evidence that was not provided.
3. The Asian Line and Myanmar Odds are LOCKED.
4. If evidence is insufficient, return PASS.
5. Do not guarantee profit.
6. Return JSON only.

Required JSON:
{{
  "status": "PICK or PASS",
  "strength": "Strong, Good, Moderate or PASS",
  "competition": "{match['league']}",
  "home": "{match['home']}",
  "away": "{match['away']}",
  "market": "{bet['market']}",
  "line": {bet['line']},
  "myanmar_odds": "{bet['myanmar_odds']}",
  "reason": "short factual reason",
  "risk": "short risk statement"
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

    response = requests.post(
        url,
        params={"key": GEMINI_API_KEY},
        json=payload,
        timeout=60,
    )

    print("GEMINI HTTP:", response.status_code)

    if response.status_code != 200:
        raise RuntimeError(
            f"GEMINI ERROR: {response.text}"
        )

    data = response.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(
            f"Gemini returned unexpected response: {data}"
        )

    return text


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 50)
    print("ANALYSIS FOOTBALL INTEGRATION TEST")
    print("=" * 50)

    # Step 1
    match = get_one_fdo_match()

    print("\nFDO MATCH")
    print(
        f"{match['league']} | "
        f"{match['mmt_time']} MMT | "
        f"{match['home']} vs {match['away']}"
    )

    # Step 2
    odds_events = get_odds_events()

    # Step 3
    odds_match = find_odds_match(
        match,
        odds_events
    )

    if not odds_match:

        print("\nRESULT: PASS")
        print(
            "FDO match found, but matching Odds API "
            "event was not found."
        )
        print(
            "NO GEMINI REQUEST SENT."
        )

        raise SystemExit(0)

    print("\nODDS MATCH FOUND")
    print(
        f"{odds_match.get('home_team')} vs "
        f"{odds_match.get('away_team')}"
    )

    # Step 4
    spreads, totals = extract_market_lines(
        odds_match
    )

    print("\nSPREAD COUNT:", len(spreads))
    print("TOTAL COUNT:", len(totals))

    # Step 5
    bet = choose_line(
        spreads,
        totals
    )

    if not bet:

        print("\nRESULT: PASS")
        print(
            "No verified wanted Asian line found."
        )
        print(
            "NO GEMINI REQUEST SENT."
        )

        raise SystemExit(0)

    print("\nVERIFIED BET")
    print(
        f"{bet['market']} | "
        f"{bet['line']} | "
        f"{bet['myanmar_odds']}"
    )
    print(
        f"Bookmaker: {bet['bookmaker']}"
    )
    print(
        f"Side: {bet['side']}"
    )
    print(
        f"Price: {bet['price']}"
    )

    # Step 6 — ONE Gemini request
    print("\nCalling Gemini once...")

    result = ask_gemini(
        match,
        bet
    )

    print("\nGEMINI RESULT")
    print(result)

    print("\n" + "=" * 50)
    print("INTEGRATION TEST FINISHED")
    print("=" * 50)
