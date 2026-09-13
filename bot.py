import os
import requests
from datetime import datetime, timezone, timedelta


# ============================================================
# ANALYSIS FOOTBALL BOT
# PRIMARY SOURCE : Football-Data.org
# TIMEZONE        : Myanmar Standard Time (UTC+6:30)
# ============================================================


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
FDO_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")


MMT = timezone(timedelta(hours=6, minutes=30))


# ============================================================
# ALLOWED COMPETITIONS
# Bot MUST NOT analyze other leagues.
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
#
# Asian / Malaysian Line  ->  Myanmar Odds
#
# This table follows the user's supplied Myanmar reference.
# DO NOT change these mappings without user approval.
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


# ============================================================
# ASIAN LINE NORMALIZATION
# ============================================================

def normalize_line(line):
    """
    Convert an Asian line into a standard float.
    Examples:
        0       -> 0.0
        "0.25"  -> 0.25
        2.5     -> 2.5
    """

    try:
        return round(float(line), 2)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid Asian line: {line}")


def asian_to_myanmar(line):
    """
    Convert Asian/Malaysian line to Myanmar odds.

    IMPORTANT:
    If the line is not in the locked table,
    do NOT guess.
    """

    line = normalize_line(line)

    if line not in MYANMAR_ODDS:
        return None

    return MYANMAR_ODDS[line]


def format_line(line):
    """
    Display Asian Line + Myanmar Odds together.

    Example:
        Asian 2.25 | Myanmar 2-50
    """

    line = normalize_line(line)
    myanmar = asian_to_myanmar(line)

    if myanmar is None:
        return "Asian Line: UNVERIFIED | Myanmar Odds: UNVERIFIED"

    return f"Asian Line: {line:g} | Myanmar Odds: {myanmar}"


# ============================================================
# SPECIAL MYANMAR ODDS EXAMPLES
#
# These are explanatory examples only.
# They are NOT live odds.
# ============================================================

MYANMAR_EXAMPLES = {
    "1-40": "1-goal line, 40% loss; at 2 goals = full win",
    "2+60": "2-goal line, 60% win; at 3 goals = full win",
    "2-20": "2-goal line, 20% loss; at 3 goals = full win",
}


# ============================================================
# CURRENT MMT DATE / TIME
# ============================================================

def now_mmt():
    return datetime.now(MMT)


def today_mmt():
    return now_mmt().date()


# ============================================================
# GET TODAY'S VERIFIED FIXTURES
#
# IMPORTANT:
# FDO gives UTC dates.
# We query around the MMT calendar day and then convert
# every match back to MMT before deciding whether it belongs
# to "today".
# ============================================================

def get_fixtures():

    if not FDO_API_KEY:
        raise RuntimeError(
            "FOOTBALL_DATA_API_KEY is missing"
        )

    today = today_mmt()

    # Start of today in Myanmar time
    start_mmt = datetime.combine(
        today,
        datetime.min.time(),
        tzinfo=MMT
    )

    # Start of tomorrow in Myanmar time
    end_mmt = start_mmt + timedelta(days=1)

    # Convert MMT boundaries to UTC
    start_utc = start_mmt.astimezone(timezone.utc)
    end_utc = end_mmt.astimezone(timezone.utc)

    # FDO accepts calendar dates
    date_from = start_utc.strftime("%Y-%m-%d")
    date_to = end_utc.strftime("%Y-%m-%d")

    print("================================")
    print("ANALYSIS FOOTBALL BOT")
    print("PRIMARY SOURCE: FDO")
    print("================================")
    print("MMT Today :", today)
    print("FDO From  :", date_from)
    print("FDO To    :", date_to)

    url = "https://api.football-data.org/v4/matches"

    headers = {
        "X-Auth-Token": FDO_API_KEY,
        "Accept": "application/json",
    }

    params = {
        "competitions": ",".join(COMPETITIONS.keys()),
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
            f"FDO API ERROR: {data.get('error')}"
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

        # Strict allowed-league filter
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

        # Never accept incomplete data
        if not home or not away or not utc_date:
            continue

        try:
            match_dt = datetime.fromisoformat(
                utc_date.replace("Z", "+00:00")
            )
        except ValueError:
            continue

        # Convert UTC -> Myanmar Time
        match_mmt = match_dt.astimezone(MMT)

        # Strict MMT calendar-day filter
        if match_mmt.date() != today:
            continue

        verified.append({
            "id": match_id,
            "league_code": code,
            "league": COMPETITIONS[code],
            "home": home,
            "away": away,
            "utc_date": utc_date,
            "mmt_date": match_mmt.strftime("%Y-%m-%d"),
            "mmt_time": match_mmt.strftime("%I:%M %p"),
            "status": status,
        })

    # Sort by kickoff time
    verified.sort(
        key=lambda x: x["utc_date"]
    )

    print("Verified MMT matches:", len(verified))

    return verified


# ============================================================
# TELEGRAM MESSAGE
# ============================================================

def create_message(matches):

    now = now_mmt()

    header = (
        "⚽ ANALYSIS FOOTBALL\n"
        "📅 Football Analysis System\n"
        f"🕐 {now.strftime('%d %b %Y')} | "
        f"{now.strftime('%I:%M %p')} MMT\n"
        "🔄 System is ready.\n"
        "📊 Match data and analysis will be published here."
    )

    lines = [
        header,
        "",
        "━━━━━━━━━━━━━━━━━━",
        "⚽ TODAY'S MATCHES",
        "━━━━━━━━━━━━━━━━━━",
        "",
    ]

    # --------------------------------------------------------
    # IMPORTANT:
    # If FDO returned ZERO matches, we do NOT automatically
    # claim "ယနေ့ပွဲမရှိပါ" unless the source response itself
    # was successfully verified.
    #
    # Here the FDO request itself was successful.
    # Therefore zero verified MMT matches means no matches
    # in the six allowed competitions for that MMT day.
    # --------------------------------------------------------

    if not matches:

        lines.append(
            "ယနေ့ခွင့်ပြုထားသော ၆ ပြိုင်ပွဲအတွင်း "
            "ပွဲမရှိပါ။"
        )

        return "\n".join(lines)

    current_league = None

    for match in matches:

        league = match["league"]

        if league != current_league:

            current_league = league

            lines.append(
                f"🏆 {league}"
            )

        lines.append(
            f"🕐 {match['mmt_time']} MMT"
        )

        lines.append(
            f"⚽ {match['home']} vs {match['away']}"
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
            "Empty Telegram message blocked"
        )

    url = (
        f"https://api.telegram.org/"
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

        print("\n==============================")
        print("VERIFIED MATCHES")
        print("==============================")

        for match in matches:

            print(
                f"{match['league']} | "
                f"{match['mmt_time']} | "
                f"{match['home']} vs "
                f"{match['away']}"
            )

        message = create_message(matches)

        print("\n==============================")
        print("TELEGRAM MESSAGE")
        print("==============================")
        print(message)
        print("==============================")

        send_telegram(message)

        print(
            "\nMessage sent successfully."
        )

    except Exception as error:

        # FAIL CLOSED
        #
        # If verification fails, do NOT send anything
        # to Telegram. This prevents fake information.

        print(
            "\nBOT STOPPED - "
            "NO UNVERIFIED DATA SENT"
        )

        print(
            "ERROR:",
            str(error)
        )

        raise
