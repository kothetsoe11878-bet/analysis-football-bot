import os
import csv
import requests
from pathlib import Path

API_URL = "https://api.football-data.org/v4/competitions"

API_TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN")

if not API_TOKEN:
    raise RuntimeError("FOOTBALL_DATA_TOKEN GitHub Secret မတွေ့ပါ")

LEAGUES = {
    "EPL": "PL",
    "La_Liga": "PD",
    "Serie_A": "SA",
    "Bundesliga": "BL1",
    "Ligue_1": "FL1",
}

OUTPUT_DIR = Path("data/results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

headers = {
    "X-Auth-Token": API_TOKEN
}


def get_matches(league_name, league_code):
    url = f"{API_URL}/{league_code}/matches"

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data.get("matches", [])


def save_csv(league_name, matches):
    filename = OUTPUT_DIR / f"{league_name.lower()}_current.csv"

    fieldnames = [
        "match_id",
        "date",
        "status",
        "matchday",
        "home_team",
        "away_team",
        "home_goals",
        "away_goals",
        "winner",
    ]

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for match in matches:

            score = match.get("score", {})
            full_time = score.get("fullTime", {})

            writer.writerow({
                "match_id": match.get("id"),
                "date": match.get("utcDate"),
                "status": match.get("status"),
                "matchday": match.get("matchday"),
                "home_team": match.get("homeTeam", {}).get("name"),
                "away_team": match.get("awayTeam", {}).get("name"),
                "home_goals": full_time.get("home"),
                "away_goals": full_time.get("away"),
                "winner": score.get("winner"),
            })

    print(
        f"{league_name}: {len(matches)} matches -> {filename}"
    )


def main():

    for league_name, league_code in LEAGUES.items():

        print(
            f"Updating {league_name}..."
        )

        matches = get_matches(
            league_name,
            league_code
        )

        save_csv(
            league_name,
            matches
        )

    print("5-League update completed.")


if __name__ == "__main__":
    main()
