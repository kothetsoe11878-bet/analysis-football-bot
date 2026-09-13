import os
import requests
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
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


def now_mmt():
    return datetime.now(MMT)


def get_today():
    return now_mmt().strftime("%Y-%m-%d")


def get_fixtures():

    if not FDO_API_KEY:
        raise RuntimeError("FOOTBALL_DATA_API_KEY is missing")

    today = get_today()

    url = "https://api.football-data.org/v4/matches"

    headers = {
        "X-Auth-Token": FDO_API_KEY,
        "Accept": "application/json",
    }

    params = {
        "competitions": ",".join(COMPETITIONS.keys()),
        "dateFrom": today,
        "dateTo": today,
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    print("FDO HTTP Status:", response.status_code)

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            f"FDO returned invalid JSON: {response.text[:500]}"
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

        verified.append({
            "league": COMPETITIONS[code],
            "home": home,
            "away": away,
            "utc_date": utc_date,
            "status": status,
        })

    return verified


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

    if not matches:
        return (
            header
            + "\n\n"
            + "━━━━━━━━━━━━━━━━━━\n"
            + "⚽ TODAY'S MATCHES\n"
            + "━━━━━━━━━━━━━━━━━━\n\n"
            + "ယနေ့ပွဲမရှိပါ။"
        )

    lines = [
        header,
        "",
        "━━━━━━━━━━━━━━━━━━",
        "⚽ TODAY'S MATCHES",
        "━━━━━━━━━━━━━━━━━━",
        "",
    ]

    current_league = None

    for match in matches:

        league = match["league"]

        if league != current_league:
            current_league = league
            lines.append(f"🏆 {league}")

        match_time = datetime.fromisoformat(
            match["utc_date"].replace("Z", "+00:00")
        ).astimezone(MMT)

        lines.append(
            f"🕐 {match_time.strftime('%I:%M %p')} MMT"
        )

        lines.append(
            f"⚽ {match['home']} vs {match['away']}"
        )

        lines.append("")

    return "\n".join(lines)


def send_telegram(message):

    if not BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing"
        )

    if not CHANNEL_USERNAME:
        raise RuntimeError(
            "CHANNEL_USERNAME is missing"
        )

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        json={
            "chat_id": CHANNEL_USERNAME,
            "text": message,
        },
        timeout=30,
    )

    print("Telegram HTTP Status:", response.status_code)
    print("Telegram response:", response.text)

    if response.status_code != 200:
        raise RuntimeError(
            f"Telegram send failed: {response.text}"
        )


if __name__ == "__main__":

    print("================================")
    print("ANALYSIS FOOTBALL BOT")
    print("FDO PRIMARY SOURCE")
    print("================================")

    matches = get_fixtures()

    print("Verified matches:", len(matches))

    message = create_message(matches)

    print("\n----- TELEGRAM MESSAGE -----")
    print(message)
    print("----------------------------")

    send_telegram(message)

    print("\nMessage sent successfully.")
