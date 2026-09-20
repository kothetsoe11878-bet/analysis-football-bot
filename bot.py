# Analysis Football Bot
# Verified Fixtures + Dynamic Asian O/U + Myanmar Odds
#
# Workflow:
#   09:00 MMT -> Result Review (not enabled yet)
#   10:00 MMT -> T-1 analysis candidates, next 7 days, max 12
#   18:00 MMT -> Final analysis, today's matches, max 4
#
# IMPORTANT:
#   - Only six allowed competitions
#   - No fixed 2.5 O/U line
#   - No invented fixture
#   - No invented odds
#   - No forced PICK
#   - If evidence is insufficient -> PASS


import os
import requests
from datetime import datetime, timezone, timedelta
from collections import Counter

from odds import display_line
from gemini_analysis import analyze_match
from sources import (
    get_today_verified_matches,
    get_t1_verified_matches,
)
from rules import workflow_stage


# ============================================================
# CONFIG
# ============================================================

MMT = timezone(timedelta(hours=6, minutes=30))

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

CHANNEL_USERNAME = os.getenv(
    "CHANNEL_USERNAME"
)

ODDS_API_KEY = os.getenv(
    "ODDS_API_KEY"
)

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

ODDS_URL = (
    "https://api.the-odds-api.com/v4/sports"
)


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
    }

    for old, new in replacements.items():
        value = value.replace(
            old,
            new
        )

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

    if not ha or not aa or not hb or not ab:
        return False

    direct_match = (
        ha == hb
        and
        aa == ab
    )

    partial_match = (
        (
            ha in hb
            or
            hb in ha
        )
        and
        (
            aa in ab
            or
            ab in aa
        )
    )

    return (
        direct_match
        or
        partial_match
    )


# ============================================================
# WORKFLOW FIXTURES
# ============================================================

def get_fixtures_for_stage(stage):

    """
    Get verified fixtures from sources.py.

    09:00 MMT:
        Result review is intentionally disabled
        until prediction history is stored.

    10:00 MMT:
        Next 7 days.

    18:00 MMT:
        Today's matches only.
    """

    if stage == "RESULT_REVIEW_9AM":

        return []

    if stage == "T1_10AM":

        return get_t1_verified_matches(
            days=7
        )

    if stage == "FINAL_6PM":

        return get_today_verified_matches()

    return []


# ============================================================
# ODDS API
# ============================================================

def get_odds_events(competition):

    """
    Get current totals/spreads odds for
    one allowed competition.
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
            "Odds API returned invalid JSON: "
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
# EXTRACT REAL O/U POINTS
# ============================================================

def extract_total_points(event):

    """
    Extract real O/U points supplied by bookmakers.

    Nothing is invented.

    Example:
        [2.5, 2.5, 3.0, 3.0]
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

                point = outcome.get(
                    "point"
                )

                if isinstance(
                    point,
                    (int, float)
                ):

                    points.append(
                        float(point)
                    )

    return points


# ============================================================
# DYNAMIC O/U LINE
# ============================================================

def choose_dynamic_ou_line(event):

    """
    Choose the most common real bookmaker O/U line.

    2.5 is NOT hard-coded.

    If several lines have equal frequency,
    use the median of the tied lines.
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
        for point, count
        in counts.items()
        if count == highest_count
    )

    middle = len(candidates) // 2

    if len(candidates) % 2 == 1:

        return candidates[middle]

    return (
        candidates[middle - 1]
        +
        candidates[middle]
    ) / 2


# ============================================================
# MATCH ODDS
# ============================================================

def get_match_odds(fixture):

    """
    Find current Odds API event for one
    verified FDO fixture.
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
                    "No current O/U totals "
                    "line was supplied "
                    "by Odds API."
                ),
                "event_id": event.get(
                    "id"
                ),
            }

        try:

            display = display_line(
                line
            )

        except ValueError as error:

            return {
                "status": "PASS",
                "reason": (
                    f"Odds API supplied "
                    f"unsupported O/U line "
                    f"{line}: {error}"
                ),
                "event_id": event.get(
                    "id"
                ),
            }

        return {
            "status": "OK",
            "event_id": event.get(
                "id"
            ),
            "market": "OU",
            "line": line,
            "myanmar_odds": (
                display.split(
                    " | ",
                    1
                )[1]
            ),
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

def run_gemini(
    fixture,
    odds,
):

    """
    Send verified fixture + current odds
    to gemini_analysis.py.

    No invented football evidence.
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
        "home": fixture[
            "home"
        ],
        "away": fixture[
            "away"
        ],
        "market": "OU",
        "line": line,
        "myanmar_odds": myanmar_odds,

        "evidence": {

            "fixture": {
                "source": (
                    "Football-Data.org"
                ),
                "mmt_date": fixture[
                    "mmt_date"
                ],
                "mmt_time": fixture[
                    "mmt_time"
                ],
            },

            "current_odds": {
                "source": (
                    "The Odds API"
                ),
                "market": "totals",
                "consensus_line": line,
                "available_lines": (
                    odds.get(
                        "raw_points",
                        []
                    )
                ),
            },
        },
    }

    result = analyze_match(
        match
    )

    # --------------------------------------------------------
    # SECURITY CHECK
    # --------------------------------------------------------

    if result.get(
        "line"
    ) != line:

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
        f"{TELEGRAM_BOT_TOKEN}"
        "/sendMessage"
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
            "Telegram API ERROR: "
            f"{response.text[:1000]}"
        )

    return response.json()


# ============================================================
# TELEGRAM MESSAGE
# ============================================================

def build_message(
    fixture,
    odds,
    analysis,
):

    competition = fixture[
        "competition"
    ]

    home = fixture[
        "home"
    ]

    away = fixture[
        "away"
    ]

    time_text = fixture[
        "mmt_time"
    ]

    # --------------------------------------------------------
    # ODDS PASS
    # --------------------------------------------------------

    if odds.get(
        "status"
    ) != "OK":

        return (
            f"⚽ {competition}\n"
            f"{home} vs {away}\n"
            f"🕒 {time_text} MMT\n\n"
            f"⏭️ O/U PASS\n"
            f"{odds.get('reason', '')}"
        )

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # PICK
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # PASS
    # --------------------------------------------------------

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
        "========================================"
    )

    print(
        "     ANALYSIS FOOTBALL BOT"
    )

    print(
        "========================================"
    )

    print(
        "Dynamic O/U line: ENABLED"
    )

    print(
        "Fixed 2.5 line: DISABLED"
    )

    # --------------------------------------------------------
    # WORKFLOW
    # --------------------------------------------------------

    stage = workflow_stage()

    print(
        f"[WORKFLOW] Stage: {stage}"
    )

    # --------------------------------------------------------
    # FIXTURES
    # --------------------------------------------------------

    try:

        fixtures = (
            get_fixtures_for_stage(
                stage
            )
        )

    except Exception as error:

        print(
            "[FIXTURE ERROR]",
            error
        )

        return

    print(
        f"[FIXTURE CHECK] "
        f"Matches found: "
        f"{len(fixtures)}"
    )

    for fixture in fixtures:

        print(
            f"[FIXTURE] "
            f"{fixture['competition']} | "
            f"{fixture['home']} vs "
            f"{fixture['away']} | "
            f"{fixture['mmt_date']} "
            f"{fixture['mmt_time']}"
        )

    # --------------------------------------------------------
    # RESULT REVIEW
    # --------------------------------------------------------

    if stage == "RESULT_REVIEW_9AM":

        print(
            "[RESULT REVIEW] "
            "Prediction history is not "
            "enabled yet."
        )

        return

    # --------------------------------------------------------
    # NO MATCHES
    # --------------------------------------------------------

    if not fixtures:

        print(
            "[NO MATCHES] "
            "No verified fixtures found "
            "for this workflow stage."
        )

        return

    # --------------------------------------------------------
    # MATCH LIMIT
    # --------------------------------------------------------

    if stage == "T1_10AM":

        max_matches = 12

    elif stage == "FINAL_6PM":

        max_matches = 4

    else:

        max_matches = 0

    fixtures = fixtures[
        :max_matches
    ]

    print(
        f"[WORKFLOW] "
        f"Processing maximum "
        f"{max_matches} matches."
    )

    # --------------------------------------------------------
    # PROCESS
    # --------------------------------------------------------

    processed = 0

    for fixture in fixtures:

        print(
            "\n----------------------------------------"
        )

        print(
            f"[MATCH {processed + 1}] "
            f"{fixture['competition']} | "
            f"{fixture['home']} vs "
            f"{fixture['away']}"
        )

        # ----------------------------------------------------
        # ODDS
        # ----------------------------------------------------

        try:

            odds = get_match_odds(
                fixture
            )

        except Exception as error:

            print(
                "[ODDS ERROR]",
                error
            )

            continue

        print(
            "[ODDS RESULT]",
            odds
        )

        # ----------------------------------------------------
        # NO ODDS -> PASS
        # ----------------------------------------------------

        if odds.get(
            "status"
        ) != "OK":

            message = build_message(
                fixture,
                odds,
                {
                    "status": "PASS",
                    "strength": "PASS",
                },
            )

            try:

                send_telegram(
                    message
                )

                print(
                    "[TELEGRAM] PASS sent."
                )

            except Exception as error:

                print(
                    "[TELEGRAM ERROR]",
                    error
                )

            processed += 1

            continue

        # ----------------------------------------------------
        # CURRENT REAL LINE
        # ----------------------------------------------------

        print(
            "[O/U LINE]",
            odds["line"]
        )

        print(
            "[MYANMAR ODDS]",
            odds["myanmar_odds"]
        )

        print(
            "[DISPLAY]",
            odds["display_line"]
        )

        # ----------------------------------------------------
        # GEMINI
        # ----------------------------------------------------

        try:

            analysis = run_gemini(
                fixture,
                odds
            )

        except Exception as error:

            print(
                "[GEMINI ERROR]",
                error
            )

            analysis = {
                "status": "PASS",
                "strength": "PASS",
                "analysis_mm": (
                    "ယခုအဆင့်တွင် "
                    "ခိုင်လုံသောသုံးသပ်ချက် "
                    "မရရှိသေးသောကြောင့် PASS "
                    "ပြုလုပ်ထားသည်။"
                ),
                "risk_mm": (
                    "အချက်အလက်မပြည့်စုံသေးသဖြင့် "
                    "လောင်းကြေးမပြုလုပ်သင့်ပါ။"
                ),
            }

        print(
            "[GEMINI RESULT]",
            analysis
        )

        # ----------------------------------------------------
        # TELEGRAM
        # ----------------------------------------------------

        message = build_message(
            fixture,
            odds,
            analysis
        )

        try:

            send_telegram(
                message
            )

            print(
                "[TELEGRAM] SENT"
            )

        except Exception as error:

            print(
                "[TELEGRAM ERROR]",
                error
            )

        processed += 1

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    print(
        "\n========================================"
    )

    print(
        f"[WORKFLOW COMPLETE] "
        f"Stage={stage} | "
        f"Processed={processed}"
    )

    print(
        "========================================"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
