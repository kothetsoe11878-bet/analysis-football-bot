import os
import csv
import requests
from pathlib import Path

API_KEY = os.environ.get("ODDS_API_KEY")

if not API_KEY:
    raise RuntimeError("ODDS_API_KEY GitHub Secret မတွေ့ပါ")

SPORTS = {
    "EPL": "soccer_epl",
    "La_Liga": "soccer_spain_la_liga",
    "Serie_A": "soccer_italy_serie_a",
    "Bundesliga": "soccer_germany_bundesliga",
    "Ligue_1": "soccer_france_ligue_one",
}

OUTPUT_DIR = Path("data/odds")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://api.the-odds-api.com/v4/sports"


def get_odds(league, sport_key):
    url = f"{BASE_URL}/{sport_key}/odds"

    params = {
        "apiKey": API_KEY,
        "regions": "eu",
        "markets": "spreads",
        "oddsFormat": "decimal",
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def save_csv(league, matches):

    filename = OUTPUT_DIR / f"{league.lower()}_odds_current.csv"

    fields = [
        "match_id",
        "commence_time",
        "home_team",
        "away_team",
        "bookmaker",
        "market",
        "home_handicap",
        "home_price",
        "away_handicap",
        "away_price",
    ]

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()

        for match in matches:

            for bookmaker in match.get("bookmakers", []):

                for market in bookmaker.get("markets", []):

                    if market.get("key") != "spreads":
                        continue

                    outcomes = market.get("outcomes", [])

                    if len(outcomes) < 2:
                        continue

                    home = next(
                        (
                            x for x in outcomes
                            if x.get("name") == match.get("home_team")
                        ),
                        None
                    )

                    away = next(
                        (
                            x for x in outcomes
                            if x.get("name") == match.get("away_team")
                        ),
                        None
                    )

                    if not home or not away:
                        continue

                    writer.writerow({
                        "match_id": match.get("id"),
                        "commence_time": match.get("commence_time"),
                        "home_team": match.get("home_team"),
                        "away_team": match.get("away_team"),
                        "bookmaker": bookmaker.get("title"),
                        "market": "spreads",
                        "home_handicap": home.get("point"),
                        "home_price": home.get("price"),
                        "away_handicap": away.get("point"),
                        "away_price": away.get("price"),
                    })

    print(
        f"{league}: {len(matches)} matches -> {filename}"
    )


def main():

    for league, sport_key in SPORTS.items():

        print(f"Updating odds: {league}")

        matches = get_odds(
            league,
            sport_key
        )

        save_csv(
            league,
            matches
        )

    print("5-League odds update completed.")


if __name__ == "__main__":
    main()
