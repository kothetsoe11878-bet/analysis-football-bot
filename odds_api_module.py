import os
import requests

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4"

SPORT_KEYS = {
    "EPL": "soccer_epl",
    "La Liga": "soccer_spain_la_liga",
    "Serie A": "soccer_italy_serie_a",
    "Bundesliga": "soccer_germany_bundesliga",
    "Ligue 1": "soccer_france_ligue_one",
    "UCL": "soccer_uefa_champs_league",
}

def get_odds(league, regions="eu", markets="h2h"):
    if not ODDS_API_KEY:
        raise RuntimeError("ODDS_API_KEY is missing")
    sport = SPORT_KEYS.get(league)
    if not sport:
        raise RuntimeError(f"Unsupported competition: {league}")

    response = requests.get(
        f"{BASE_URL}/sports/{sport}/odds",
        params={
            "apiKey": ODDS_API_KEY,
            "regions": regions,
            "markets": markets,
            "oddsFormat": "decimal",
        },
        timeout=30,
    )
    try:
        data = response.json()
    except ValueError:
        raise RuntimeError("Odds API returned invalid JSON")

    if response.status_code != 200:
        raise RuntimeError(f"Odds API HTTP {response.status_code}: {data}")

    return data, response.headers

def summarize(league="EPL"):
    data, headers = get_odds(league, regions="eu", markets="h2h")
    print(f"League: {league}")
    print(f"Events returned: {len(data)}")
    print(f"Quota remaining: {headers.get('x-requests-remaining', 'unknown')}")
    print(f"Quota used: {headers.get('x-requests-used', 'unknown')}")
    print(f"Last request cost: {headers.get('x-requests-last', 'unknown')}")
    for event in data[:5]:
        print(f"- {event.get('home_team')} vs {event.get('away_team')} | {event.get('commence_time')}")
    return data
