# Analysis Football Bot
# Dynamic match-specific Asian O/U + Myanmar Odds
# 2.5 is NOT hard-coded.

import os
import requests
from datetime import datetime, timezone, timedelta
from collections import Counter

from odds import display_line
from gemini_analysis import analyze_match


# ============================================================
# CONFIG
# ============================================================

MMT = timezone(timedelta(hours=6, minutes=30))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

FDO_URL = "https://api.football-data.org/v4/matches"
ODDS_URL = "https://api.the-odds-api.com/v4/sports"

# ONLY these six competitions
COMPETITIONS = {
    "PL": "EPL",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "CL": "UCL",
}

# The Odds API sport keys
ODDS_SPORTS = {
    "EPL": "soccer_epl",
    "La Liga": "soccer_spain_la_liga",
    "Serie A": "soccer_italy_serie_a",
    "Bundesliga": "soccer_germany_bundesliga",
    "Ligue 1": "soccer_france_ligue_one",
    "UCL": "soccer_uefa_champs_league",
}


# ============================================================
# TIME
# ============================================================

def now_mmt():
    return datetime.now(MMT)


# ============================================================
# FOOTBALL-DATA.ORG
# ============================================================

def get_fixtures():
    """
    Get today's upcoming fixtures in Myanmar time
    from the six allowed competitions only.
    """

    if not FOOTBALL_DATA_API_KEY:
        raise RuntimeError(
            "FOOTBALL_DATA_API_KEY is missing."
        )

    now = now_mmt()
    today = now.date()

    start_mmt = datetime.combine(
        today,
        datetime.min.time(),
        tzinfo=MMT,
    )

    end_mmt = start_mmt + timedelta(days=1)

    date_from = start_mmt.astimezone(
        timezone.utc
    ).strftime("%Y-%m-%d")

    date_to = end_mmt.astimezone(
        timezone.utc
    ).strftime("%Y-%m-%d")

    headers = {
        "X-Auth-Token": FOOTBALL_DATA_API_KEY,
        "Accept": "application/json",
    }

    params = {
        "competitions": ",".join(
            COMPETITIONS.keys()
        ),
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
            f"FDO returned invalid JSON: "
            f"{response.text[:500]}"
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"FDO API ERROR: {data}"
        )

    matches = data.get("matches")

    if matches is None:
        raise RuntimeError(
            "FDO response has no matches field."
        )

    fixtures = []

    for match in matches:

        competition = match.get(
            "competition", {}
        )

        code = competition.get("code")

        if code not in COMPETITIONS:
            continue

        home = match.get(
            "homeTeam", {}
        ).get("name")

        away = match.get(
            "awayTeam", {}
        ).get("name")

        utc_date = match.get("utcDate")

        if not home or not away or not utc_date:
            continue

        try:
            match_dt = datetime.fromisoformat(
                utc_date.replace(
                    "Z",
                    "+00:00"
                )
            )
        except ValueError:
            continue

        match_mmt = match_dt.astimezone(MMT)

        if match_mmt.date() != today:
            continue

        if match_mmt <= now:
            continue

        fixtures.append({
            "id": match.get("id"),
            "competition_code": code,
            "competition": COMPETITIONS[code],
            "home": home,
            "away": away,
            "utc_date": utc_date,
            "mmt_datetime": match_mmt,
            "mmt_time": match_mmt.strftime(
                "%I:%M %p"
            ),
        })

    fixtures.sort(
        key=lambda x: x["mmt_datetime"]
    )

    return fixtures


# ============================================================
# TEAM NAME NORMALIZATION
# ============================================================

def normalize_name(name):
    if not name:
        return ""

    value = name.lower()

    replacements = {
        "fc": "",
        "cf": "",
        "afc": "",
        "ac": "",
        "sc": "",
        "1. fc": "",
        "real ": "real ",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return (
        value
        .replace(".", "")
        .replace("-", " ")
        .replace("_", " ")
        .replace("'", "")
        .strip()
    )


def teams_match(
    home_a,
    away_a,
    home_b,
    away_b,
):
    ha = normalize_name(home_a)
    aa = normalize_name(away_a)
    hb = normalize_name(home_b)
    ab = normalize_name(away_b)

    return (
        (ha == hb and aa == ab)
        or
        (
            ha in hb
            or hb in ha
        )
        and
        (
            aa in ab
            or ab in aa
        )
    )


# ============================================================
# ODDS API
# ============================================================

def get_odds_events(competition):
    """
    Get current odds for one allowed competition.

    IMPORTANT:
    We request totals/spreads from the Odds API.
    We do NOT set O/U line to 2.5.
    """

    if not ODDS_API_KEY:
        raise RuntimeError(
            "ODDS_API_KEY is missing."
        )

    sport_key = ODDS_SPORTS.get(
        competition
    )

    if not sport_key:
        raise RuntimeError(
            f"No Odds API sport key for "
            f"{competition}"
        )

    url = (
        f"{ODDS_URL}/"
        f"{sport_key}/odds"
    )

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "totals,spreads",
        "oddsFormat": "decimal",
    }

    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            f"Odds API returned invalid JSON: "
            f"{response.text[:500]}"
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Odds API ERROR: {data}"
        )

    if not isinstance(data, list):
        raise RuntimeError(
            "Odds API returned unexpected data."
        )

    return data


# ============================================================
# MATCH-SPECIFIC O/U LINE
# ============================================================

def extract_total_points(event):
    """
    Extract every actual O/U point supplied by bookmakers
    for this specific match.

    Example:
        [2.5, 2.5, 3.0, 3.0, 3.0]

    Nothing is invented.
    """

    points = []

    bookmakers = event.get(
        "bookmakers",
        []
    )

    for bookmaker in bookmakers:

        markets = bookmaker.get(
            "markets",
            []
        )

        for market in markets:

            if market.get("key") != "totals":
                continue

            outcomes = market.get(
                "outcomes",
                []
            )

            for outcome in outcomes:

                if outcome.get("name") not in {
                    "Over",
                    "Under",
                }:
                    continue

                point = outcome.get("point")

                if isinstance(
                    point,
                    (int, float)
                ):
                    points.append(
                        float(point)
                    )

    return points


def choose_dynamic_ou_line(event):
    """
    Choose the consensus/main current O/U line.

    We DO NOT assume 2.5.

    Method:
      1. Collect all bookmaker total-goal points.
      2. Find the most common point.
      3. If multiple points have equal frequency,
         choose the median among the tied points.

    Returns None if no real totals line exists.
    """

    points = extract_total_points(
        event
    )

    if not points:
        return None

    counts = Counter(points)

    highest_count = max(
        counts.values()
    )

    candidates = sorted(
        point
        for point, count in counts.items()
        if count == highest_count
    )

    middle = len(candidates) // 2

    if len(candidates) % 2 == 1:
        return candidates[middle]

    return (
        candidates[middle - 1]
        + candidates[middle]
    ) / 2


# ============================================================
# GET ODDS FOR ONE MATCH
# ============================================================

def get_match_odds(fixture):
    """
    Find the Odds API event corresponding to one FDO fixture.

    Returns:
      {
        "market": "OU",
        "line": actual line,
        "myanmar_odds": actual mapped Myanmar notation,
        "bookmakers": ...
      }

    No fixed 2.5.
    """

    competition = fixture[
        "competition"
    ]

    events = get_odds_events(
        competition
    )

    for event in events:

        if not teams_match(
            fixture["home"],
            fixture["away"],
            event.get("home_team"),
            event.get("away_team"),
        ):
            continue

        line = choose_dynamic_ou_line(
            event
        )

        if line is None:
            return {
                "status": "PASS",
                "reason": (
                    "No current O/U totals line "
                    "was supplied by Odds API."
                ),
                "event_id": event.get("id"),
            }

        try:
            display = display_line(
                line
            )
        except ValueError as error:
            return {
                "status": "PASS",
                "reason": (
                    f"Odds API supplied unsupported "
                    f"O/U line {line}: {error}"
                ),
                "event_id": event.get("id"),
            }

        return {
            "status": "OK",
            "event_id": event.get("id"),
            "market": "OU",
            "line": line,
            "myanmar_odds": display.split(
                " | ",
                1
            )[1],
            "display_line": display,
            "raw_points": sorted(
                set(
                    extract_total_points(
                        event
                    )
                )
            ),
        }

    return {
        "status": "PASS",
        "reason": (
            "Matching Odds API event "
            "was not found."
        ),
    }


# ============================================================
# GEMINI
# ============================================================

def run_gemini(fixture, odds):
    """
    Send only verified fixture + current odds
    to the tested Gemini module.
    """

    if odds.get("status") != "OK":
        return {
            "status": "PASS",
            "reason": odds.get(
                "reason",
                "Current O/U odds unavailable."
            ),
        }

    line = odds["line"]
    myanmar_odds = odds[
        "myanmar_odds"
    ]

    match = {
        "competition": fixture[
            "competition"
        ],
        "home": fixture["home"],
        "away": fixture["away"],
        "market": "OU",
        "line": line,
        "myanmar_odds": myanmar_odds,
        "evidence": {
            "fixture": {
                "source": "Football-Data.org",
                "mmt_time": fixture[
                    "mmt_time"
                ],
            },
            "current_odds": {
                "source": "The Odds API",
                "market": "totals",
                "consensus_line": line,
                "available_lines": odds.get(
                    "raw_points",
                    []
                ),
            },
        },
    }

    result = analyze_match(
        match
    )

    # SECURITY CHECK
    # These must remain exactly equal
    # to the actual supplied market line.
    if result.get("line") != line:
        raise RuntimeError(
            "SECURITY ERROR: Gemini changed "
            "the supplied O/U line."
        )

    if result.get(
        "myanmar_odds"
    ) != myanmar_odds:
        raise RuntimeError(
            "SECURITY ERROR: Gemini changed "
            "the supplied Myanmar odds."
        )

    return result


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing."
        )

    if not CHANNEL_USERNAME:
        raise RuntimeError(
            "CHANNEL_USERNAME is missing."
        )

    url = (
        "https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": CHANNEL_USERNAME,
        "text": message,
    }

    response = requests.post(
        url,
        json=payload,
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Telegram API ERROR: "
            f"{response.text[:1000]}"
        )

    return response.json()


# ============================================================
# MESSAGE
# ============================================================

def build_message(
    fixture,
    odds,
    analysis,
):

    competition = fixture[
        "competition"
    ]

    home = fixture["home"]
    away = fixture["away"]
    time_text = fixture[
        "mmt_time"
    ]

    if odds.get("status") != "OK":

        return (
            f"⚽ {competition}\n"
            f"{home} vs {away}\n"
            f"🕒 {time_text} MMT\n\n"
            f"⏭️ O/U PASS\n"
            f"Reason: {odds.get('reason', '')}"
        )

    line_text = odds[
        "display_line"
    ]

    status = analysis.get(
        "status",
        "PASS"
    )

    strength = analysis.get(
        "strength",
        "PASS"
    )

    analysis_mm = analysis.get(
        "analysis_mm",
        ""
    )

    risk_mm = analysis.get(
        "risk_mm",
        ""
    )

    final_pick_mm = analysis.get(
        "final_pick_mm",
        ""
    )

    if status == "PICK":

        return (
            f"⚽ {competition}\n"
            f"{home} vs {away}\n"
            f"🕒 {time_text} MMT\n\n"
            f"📊 O/U: {line_text}\n"
            f"🎯 {status} | {strength}\n\n"
            f"{analysis_mm}\n\n"
            f"⚠️ Risk: {risk_mm}\n"
            f"✅ {final_pick_mm}"
        )

    return (
        f"⚽ {competition}\n"
        f"{home} vs {away}\n"
        f"🕒 {time_text} MMT\n\n"
        f"📊 O/U: {line_text}\n"
        f"⏭️ PASS\n\n"
        f"{analysis_mm}\n\n"
        f"⚠️ {risk_mm}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=== ANALYSIS FOOTBALL BOT ==="
    )

    print(
        "Dynamic O/U line mode: ENABLED"
    )

    print(
        "Fixed 2.5 line: DISABLED"
    )

    fixtures = get_fixtures()

    print(
        f"FDO upcoming fixtures: "
        f"{len(fixtures)}"
    )

    if not fixtures:
        print(
            "No upcoming allowed match today."
        )
        return

    # For the first integration stage,
    # process ONE match only.
    #
    # This deliberately limits API usage
    # while we verify the dynamic-line flow.
    fixture = fixtures[0]

    print(
        f"\nMATCH: "
        f"{fixture['competition']} | "
        f"{fixture['home']} vs "
        f"{fixture['away']}"
    )

    odds = get_match_odds(
        fixture
    )

    print(
        "ODDS RESULT:",
        odds
    )

    if odds.get("status") != "OK":

        message = build_message(
            fixture,
            odds,
            {
                "status": "PASS",
                "strength": "PASS",
            },
        )

        send_telegram(
            message
        )

        print(
            "Telegram PASS message sent."
        )

        return

    print(
        "ACTUAL O/U LINE:",
        odds["line"]
    )

    print(
        "MYANMAR ODDS:",
        odds["myanmar_odds"]
    )

    print(
        "DISPLAY:",
        odds["display_line"]
    )

    analysis = run_gemini(
        fixture,
        odds
    )

    print(
        "\n=== GEMINI RESULT ==="
    )

    print(
        analysis
    )

    message = build_message(
        fixture,
        odds,
        analysis
    )

    send_telegram(
        message
    )

    print(
        "\nTELEGRAM: SENT"
    )


if __name__ == "__main__":
    main()
