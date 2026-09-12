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

        print(f"\n========== {league_name} ==========")
        print(f"Request date: {today}")
        print(f"League ID: {league_id}")
        print("Sending request...")

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=30,
            )
        except requests.RequestException as e:
            raise RuntimeError(
                f"NETWORK ERROR for {league_name}: {e}"
            )

        print(f"HTTP Status: {response.status_code}")

        try:
            data = response.json()
        except ValueError:
            raise RuntimeError(
                f"INVALID JSON from API for {league_name}: "
                f"{response.text[:500]}"
            )

        print("API errors:", data.get("errors"))
        print("API results:", data.get("results"))

        # Show the exact API error
        if data.get("errors"):
            raise RuntimeError(
                f"API ERROR for {league_name}: "
                f"{data.get('errors')}"
            )

        # HTTP error
        if response.status_code != 200:
            raise RuntimeError(
                f"HTTP ERROR for {league_name}: "
                f"HTTP {response.status_code} | "
                f"{data}"
            )

        if "response" not in data:
            raise RuntimeError(
                f"INVALID API RESPONSE for {league_name}: "
                f"{data}"
            )

        for match in data["response"]:

            fixture = match.get("fixture")
            teams = match.get("teams")

            if not fixture or not teams:
                raise RuntimeError(
                    f"INCOMPLETE FIXTURE DATA for {league_name}: "
                    f"{match}"
                )

            home = teams.get("home", {}).get("name")
            away = teams.get("away", {}).get("name")

            if not home or not away:
                raise RuntimeError(
                    f"INCOMPLETE TEAM DATA for {league_name}: "
                    f"{match}"
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

    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

    if not CHANNEL_USERNAME:
        raise RuntimeError("CHANNEL_USERNAME is missing")

    if not text:
        raise RuntimeError("Message is empty")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": CHANNEL_USERNAME,
            "text": text,
        },
        timeout=30,
    )

    print("Telegram HTTP Status:", response.status_code)
    print("Telegram response:", response.text)

    response.raise_for_status()


if __name__ == "__main__":

    print("========================================")
    print("ANALYSIS FOOTBALL BOT - API DEBUG TEST")
    print("========================================")

    print("MMT Date:", get_mmt_date())

    matches = get_fixtures()

    print("\nTotal verified matches:", len(matches))

    message = create_output(matches)

    send_message(message)

    print("\nVerified fixture data sent successfully.")
