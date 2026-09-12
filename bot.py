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


def get_mmt_date():
    return datetime.now(MMT).strftime("%Y-%m-%d")


def get_fixtures():
    today = get_mmt_date()

    if not FOOTBALL_API_KEY:
        raise RuntimeError("FOOTBALL_API_KEY is missing")


    url = "https://v3.football.api-sports.io/fixtures"

    headers = {
        "x-apisports-key": FOOTBALL_API_KEY,
        "Accept": "application/json",
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

        if response.status_code != 200:
            raise RuntimeError(
                f"API request failed: HTTP {response.status_code}"
            )

        data = response.json()

        # Never trust an unsuccessful API response.
        if data.get("errors"):
            raise RuntimeError(
                f"API returned an error for {league_name}"
            )

        if "response" not in data:
            raise RuntimeError(
                f"Invalid API response for {league_name}"
            )

        for match in data["response"]:

            fixture = match.get("fixture")
            teams = match.get("teams")

            if not fixture or not teams:
                raise RuntimeError(
                    f"Incomplete fixture data for {league_name}"
                )

            home = teams.get("home", {}).get("name")
            away = teams.get("away", {}).get("name")

            if not home or not away:
                raise RuntimeError(
                    f"Incomplete team data for {league_name}"
                )

            all_matches.append({
                "league": league_name,
                "time": fixture["date"],
                "home": home,
                "away": away,
            })

    return all_matches


def create_output(matches):

    today = datetime.now(MMT).strftime("%d %B %Y")

    # Only after ALL six league requests succeeded
    # can we safely say there are no matches.
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


def send_message(text):

    if not text:
        return

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


if __name__ == "__main__":

    # FAIL-CLOSED:
    # If anything is wrong with the data,
    # NOTHING is sent to Telegram.

    matches = get_fixtures()

    message = create_output(matches)

    send_message(message)

    print("Verified fixture data sent successfully.")
