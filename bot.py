import os
import requests
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

MMT = timezone(timedelta(hours=6, minutes=30))

ALLOWED_LEAGUES = {
    39: "EPL",
    140: "La Liga",
    135: "Serie A",
    78: "Bundesliga",
    61: "Ligue 1",
    2: "UCL",
}


def get_fixtures():
    today = datetime.now(MMT).strftime("%Y-%m-%d")

    url = "https://v3.football.api-sports.io/fixtures"

    headers = {
        "x-apisports-key": FOOTBALL_API_KEY
    }

    all_matches = []

    for league_id, league_name in ALLOWED_LEAGUES.items():

        params = {
            "league": league_id,
            "season": 2026,
            "date": today,
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        for match in data.get("response", []):
            fixture = match["fixture"]
            teams = match["teams"]

            all_matches.append({
                "league": league_name,
                "time": fixture["date"],
                "home": teams["home"]["name"],
                "away": teams["away"]["name"],
            })

    return all_matches


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": CHANNEL_USERNAME,
            "text": text,
        },
        timeout=30,
    )

    response.raise_for_status()


def create_output(matches):

    today = datetime.now(MMT).strftime("%d %B %Y")

    if not matches:
        return (
            "⚽ ယနေ့ဘောလုံးပွဲ\n\n"
            f"📅 {today}\n\n"
            "ယနေ့ပွဲမရှိပါ။"
        )

    lines = [
        "⚽ ယနေ့ဘောလုံးပွဲများ",
        "",
        f"📅 {today}",
        "",
    ]

    current_league = None

    for match in matches:

        if match["league"] != current_league:
            current_league = match["league"]
            lines.append(f"🏆 {current_league}")

        match_time = datetime.fromisoformat(
            match["time"].replace("Z", "+00:00")
        ).astimezone(MMT)

        lines.append(
            f"🕐 {match_time.strftime('%I:%M %p')} — "
            f"{match['home']} vs {match['away']}"
        )

        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":

    matches = get_fixtures()

    message = create_output(matches)

    send_message(message)

    print("Football fixture data sent successfully.")
