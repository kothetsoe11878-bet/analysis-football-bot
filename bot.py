import os
import requests
from datetime import datetime, timezone, timedelta
from collections import defaultdict


# ============================================================
# ANALYSIS FOOTBALL BOT
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
FDO_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

MMT = timezone(timedelta(hours=6, minutes=30))


# ============================================================
# ALLOWED COMPETITIONS
# ============================================================

COMPETITIONS = {
    "PL": "EPL",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "CL": "UCL",
}


# ============================================================
# MYANMAR ODDS CONVERSION
# LOCKED REFERENCE
# ============================================================

MYANMAR_ODDS = {
    0.00: "DRAW",

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
    4.75: "5+50",

    5.00: "5D",
}


def asian_to_myanmar(line):

    try:
        line = round(float(line), 2)
    except (TypeError, ValueError):
        return None

    return MYANMAR_ODDS.get(line)


def format_odds(line):

    myanmar = asian_to_myanmar(line)

    if myanmar is None:
        return (
            f"Asian Line: {line} | "
            "Myanmar Odds: UNVERIFIED"
        )

    return (
        f"Asian Line: {line:g} | "
        f"Myanmar Odds: {myanmar}"
    )


# ============================================================
# TIME
# ============================================================

def now_mmt():
    return datetime.now(MMT)


# ============================================================
# GET TODAY'S UPCOMING MATCHES
#
# IMPORTANT:
# 1. Determine TODAY using MMT.
# 2. Convert every FDO UTC kickoff to MMT.
# 3. Keep ONLY matches:
#       - on today's MMT date
#       - not already started
# 4. Therefore finished matches are never shown as upcoming.
# ============================================================

def get_fixtures():

    if not FDO_API_KEY:
        raise RuntimeError(
            "FOOTBALL_DATA_API_KEY is missing"
        )

    now = now_mmt()
    today = now.date()

    # --------------------------------------------------------
    # Query UTC dates covering the complete MMT day.
    # --------------------------------------------------------

    start_mmt = datetime.combine(
        today,
        datetime.min.time(),
        tzinfo=MMT
    )

    end_mmt = start_mmt + timedelta(days=1)

    start_utc = start_mmt.astimezone(timezone.utc)
    end_utc = end_mmt.astimezone(timezone.utc)

    date_from = start_utc.strftime("%Y-%m-%d")
    date_to = end_utc.strftime("%Y-%m-%d")

    print("================================")
    print("ANALYSIS FOOTBALL BOT")
    print("================================")
    print("Current MMT:", now.strftime(
        "%Y-%m-%d %I:%M:%S %p"
    ))
    print("MMT Today:", today)
    print("FDO dateFrom:", date_from)
    print("FDO dateTo:", date_to)

    url = "https://api.football-data.org/v4/matches"

    headers = {
        "X-Auth-Token": FDO_API_KEY,
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
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    print("FDO HTTP Status:", response.status_code)

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            "FDO returned invalid JSON"
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"FDO API ERROR: {data}"
        )

    if data.get("error"):
        raise RuntimeError(
            f"FDO API ERROR: {data['error']}"
        )

    matches = data.get("matches")

    if matches is None:
        raise RuntimeError(
            "FDO response has no matches field"
        )

    verified = []

    for match in matches:

        competition = match.get(
            "competition",
            {}
        )

        code = competition.get("code")

        # Only allowed 6 competitions
        if code not in COMPETITIONS:
            continue

        home = match.get(
            "homeTeam",
            {}
        ).get("name")

        away = match.get(
            "awayTeam",
            {}
        ).get("name")

        utc_date = match.get("utcDate")
        status = match.get("status")
        match_id = match.get("id")

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

        # UTC -> MMT
        match_mmt = match_dt.astimezone(MMT)

        # ----------------------------------------------------
        # CRITICAL FILTER #1
        # Must belong to TODAY in Myanmar.
        # ----------------------------------------------------

        if match_mmt.date() != today:
            continue

        # ----------------------------------------------------
        # CRITICAL FILTER #2
        # Must NOT already have started.
        #
        # This prevents yesterday / finished matches from
        # appearing as today's upcoming matches.
        # ----------------------------------------------------

        if match_mmt <= now:
            continue

        verified.append({
            "id": match_id,
            "league_code": code,
            "league": COMPETITIONS[code],
            "home": home,
            "away": away,
            "utc_date": utc_date,
            "mmt_datetime": match_mmt,
            "mmt_time": match_mmt.strftime(
                "%I:%M %p"
            ),
            "status": status,
        })

    # --------------------------------------------------------
    # Sort by kickoff time
    # --------------------------------------------------------

    verified.sort(
        key=lambda x: x["mmt_datetime"]
    )

    print(
        "Upcoming verified matches:",
        len(verified)
    )

    return verified


# ============================================================
# GROUP MATCHES BY LEAGUE
# ============================================================

def group_by_league(matches):

    grouped = defaultdict(list)

    for match in matches:
        grouped[match["league"]].append(match)

    # Keep official order
    league_order = [
        "EPL",
        "La Liga",
        "Serie A",
        "Bundesliga",
        "Ligue 1",
        "UCL",
    ]

    result = {}

    for league in league_order:

        if league in grouped:
            result[league] = sorted(
                grouped[league],
                key=lambda x: x["mmt_datetime"]
            )

    return result


# ============================================================
# TELEGRAM MESSAGE
# ============================================================

def create_message(matches):

    now = now_mmt()

    lines = [
        "⚽ ANALYSIS FOOTBALL",
        "📅 Football Analysis System",
        (
            f"🕐 {now.strftime('%d %b %Y')} | "
            f"{now.strftime('%I:%M %p')} MMT"
        ),
        "🔄 System is ready.",
        "📊 Match data and analysis will be published here.",
        "",
        "━━━━━━━━━━━━━━━━━━",
        "⚽ TODAY'S UPCOMING MATCHES",
        "━━━━━━━━━━━━━━━━━━",
        "",
    ]

    # --------------------------------------------------------
    # NO UPCOMING MATCHES
    # --------------------------------------------------------

    if not matches:

        lines.append(
            "ယနေ့အတွက် လက်ကျန်ပွဲ မရှိပါ။"
        )

        return "\n".join(lines)

    # --------------------------------------------------------
    # GROUP BY LEAGUE
    # --------------------------------------------------------

    grouped = group_by_league(matches)

    for league, league_matches in grouped.items():

        lines.append(
            f"🏆 {league}"
        )

        for match in league_matches:

            lines.append(
                f"🕐 {match['mmt_time']} MMT"
            )

            lines.append(
                f"⚽ {match['home']} vs "
                f"{match['away']}"
            )

            lines.append("")

    return "\n".join(lines)


# ============================================================
# TELEGRAM SEND
# ============================================================

def send_telegram(message):

    if not BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing"
        )

    if not CHANNEL_USERNAME:
        raise RuntimeError(
            "CHANNEL_USERNAME is missing"
        )

    if not message:
        raise RuntimeError(
            "Empty message blocked"
        )

    url = (
        "https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": CHANNEL_USERNAME,
        "text": message,
    }

    response = requests.post(
        url,
        json=payload,
        timeout=30
    )

    print(
        "Telegram HTTP Status:",
        response.status_code
    )

    print(
        "Telegram response:",
        response.text
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Telegram send failed: "
            f"{response.text}"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    try:

        matches = get_fixtures()

        print("")
        print("==============================")
        print("UPCOMING MATCHES")
        print("==============================")

        for match in matches:

            print(
                f"{match['league']} | "
                f"{match['mmt_time']} | "
                f"{match['home']} vs "
                f"{match['away']}"
            )

        message = create_message(matches)

        print("")
        print("==============================")
        print("TELEGRAM MESSAGE")
        print("==============================")
        print(message)
        print("==============================")

        send_telegram(message)

        print(
            "Message sent successfully."
        )

    except Exception as error:

        # ----------------------------------------------------
        # FAIL CLOSED
        #
        # If verification fails:
        # DO NOT SEND ANYTHING.
        # ----------------------------------------------------

        print("")
        print(
            "BOT STOPPED - "
            "NO UNVERIFIED DATA SENT"
        )

        print(
            "ERROR:",
            str(error)
        )

        raise
