import os
import csv
import requests
from pathlib import Path

API_URL = "https://v3.football.api-sports.io/fixtures"

API_KEY = os.environ.get("FOOTBALL_API_KEY")

if not API_KEY:
    raise RuntimeError("FOOTBALL_API_KEY GitHub Secret မတွေ့ပါ")

LEAGUES = {
    "EPL": 39,
    "La Liga": 140,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61,
}

SEASON = 2026

OUTPUT_DIR = Path("data/results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

headers = {
    "x-apisports-key": API_KEY
}


def get_fixtures(league_name, league_id):
    params = {
        "league": league_id,
        "season": SEASON
    }

    response = requests.get(
        API_URL,
        headers=headers,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if data.get("errors"):
        raise RuntimeError(
            f"{league_name} API error: {data['errors']}"
        )

    return data.get("response", [])


def save_csv(league_name, fixtures):
    filename = OUTPUT_DIR / (
        league_name.lower()
        .replace(" ", "_")
        .replace("í", "i")
        + "_2026_27.csv"
    )

    rows = []

    for item in fixtures:
        fixture = item.get("fixture", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})
        league = item.get("league", {})

        rows.append({
            "fixture_id": fixture.get("id"),
            "date": fixture.get("date"),
            "status": fixture.get("status", {}).get("short"),
            "league": league.get("name"),
            "season": league.get("season"),
            "round": league.get("round"),
            "home_team": teams.get("home", {}).get("name"),
            "away_team": teams.get("away", {}).get("name"),
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
            "home_winner": teams.get("home", {}).get("winner"),
            "away_winner": teams.get("away", {}).get("winner"),
        })

    fieldnames = [
        "fixture_id",
        "date",
        "status",
        "league",
        "season",
        "round",
        "home_team",
        "away_team",
        "home_goals",
        "away_goals",
        "home_winner",
        "away_winner",
    ]

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"{league_name}: {len(rows)} matches -> {filename}"
    )


def main():
    for league_name, league_id in LEAGUES.items():
        print(f"Updating {league_name}...")

        fixtures = get_fixtures(
            league_name,
            league_id
        )

        save_csv(
            league_name,
            fixtures
        )

    print("5-League update completed.")


if __name__ == "__main__":
    main()
