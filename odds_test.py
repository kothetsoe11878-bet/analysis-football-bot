import os
import requests
from datetime import datetime, timezone, timedelta

API_KEY = os.getenv("FOOTBALL_API_KEY")

MMT = timezone(timedelta(hours=6, minutes=30))

TARGET_TEAMS = {
    "Juventus FC",
    "US Sassuolo Calcio",
    "Paris Saint-Germain FC",
    "Stade Brestois 29",
    "Real Sociedad de Fútbol",
    "Club Atlético de Madrid",
}

def get_today_mmt():
    return datetime.now(MMT).date()

def get_fixtures():
    if not API_KEY:
        raise RuntimeError("FOOTBALL_API_KEY is missing")

    today = get_today_mmt().strftime("%Y-%m-%d")

    url = "https://v3.football.api-sports.io/fixtures"

    headers = {
        "x-apisports-key": API_KEY,
        "Accept": "application/json",
    }

    params = {
        "date": today,
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    print("FIXTURES HTTP:", response.status_code)

    data = response.json()

    if response.status_code != 200:
        raise RuntimeError(f"API-Football error: {data}")

    if data.get("errors"):
        raise RuntimeError(f"API-Football errors: {data['errors']}")

    fixtures = []

    for item in data.get("response", []):
        fixture = item.get("fixture", {})
        teams = item.get("teams", {})
        league = item.get("league", {})

        home = teams.get("home", {}).get("name")
        away = teams.get("away", {}).get("name")
        fixture_id = fixture.get("id")

        if not home or not away or not fixture_id:
            continue

        if home in TARGET_TEAMS or away in TARGET_TEAMS:
            fixtures.append({
                "id": fixture_id,
                "league": league.get("name"),
                "home": home,
                "away": away,
                "date": fixture.get("date"),
            })

    return fixtures


def get_odds(fixture_id):
    url = "https://v3.football.api-sports.io/odds"

    headers = {
        "x-apisports-key": API_KEY,
        "Accept": "application/json",
    }

    params = {
        "fixture": fixture_id,
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    print(
        f"ODDS HTTP [{fixture_id}]:",
        response.status_code
    )

    data = response.json()

    if response.status_code != 200:
        raise RuntimeError(f"Odds API error: {data}")

    if data.get("errors"):
        raise RuntimeError(f"Odds API errors: {data['errors']}")

    return data


def main():
    print("================================")
    print("ANALYSIS FOOTBALL - ODDS TEST")
    print("================================")

    fixtures = get_fixtures()

    print("Matched fixtures:", len(fixtures))

    if not fixtures:
        print("NO TARGET FIXTURES FOUND")
        return

    for match in fixtures:
        print("")
        print("--------------------------------")
        print(
            f"{match['home']} vs {match['away']}"
        )
        print("League:", match["league"])
        print("Fixture ID:", match["id"])
        print("Date:", match["date"])

        odds_data = get_odds(match["id"])

        response = odds_data.get("response", [])

        if not response:
            print("NO ODDS AVAILABLE")
            continue

        print("ODDS FOUND")

        for bookmaker in response:
            bookmaker_info = bookmaker.get("bookmaker", {})
            name = bookmaker_info.get("name")

            print("BOOKMAKER:", name)

            for bet in bookmaker_info.get("bets", []):
                bet_name = bet.get("name")

                if bet_name in (
                    "Asian Handicap",
                    "Goals Over/Under",
                ):
                    print("BET TYPE:", bet_name)

                    for value in bet.get("values", []):
                        print(
                            "VALUE:",
                            value.get("value"),
                            "| ODDS:",
                            value.get("odd"),
                        )


if __name__ == "__main__":
    main()
