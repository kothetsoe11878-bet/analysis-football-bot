import os
import requests

API_KEY = os.getenv("ODDS_API_KEY")
URL = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"

def main():
    if not API_KEY:
        raise RuntimeError("ODDS_API_KEY is missing")

    r = requests.get(
        URL,
        params={
            "apiKey": API_KEY,
            "regions": "eu",
            "markets": "spreads,totals",
            "oddsFormat": "decimal",
        },
        timeout=30,
    )

    try:
        data = r.json()
    except ValueError:
        raise RuntimeError("Odds API returned invalid JSON")

    print("HTTP:", r.status_code)
    print("Requests remaining:", r.headers.get("x-requests-remaining", "unknown"))
    print("Requests used:", r.headers.get("x-requests-used", "unknown"))
    print("Last request cost:", r.headers.get("x-requests-last", "unknown"))

    if r.status_code != 200:
        raise RuntimeError(f"Odds API ERROR: {data}")

    spreads = set()
    totals = set()

    for event in data:
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market.get("key") == "spreads":
                    for o in market.get("outcomes", []):
                        if "point" in o:
                            spreads.add(float(o["point"]))
                elif market.get("key") == "totals":
                    for o in market.get("outcomes", []):
                        if "point" in o:
                            totals.add(float(o["point"]))

    print("Events returned:", len(data))
    print("Spread lines found:", sorted(spreads))
    print("Total lines found:", sorted(totals))

    wanted_spreads = {-0.25, -0.5, -0.75, -1.0}
    wanted_totals = {2.25, 2.5, 2.75, 3.0}

    print("Wanted AH lines found:", sorted(wanted_spreads & spreads))
    print("Wanted O/U lines found:", sorted(wanted_totals & totals))

    if not spreads and not totals:
        raise RuntimeError("FAIL: No EPL spreads/totals point data returned.")

    print("PASS: EPL spread/total point data returned.")
    print("NEXT: Check exact Asian-line coverage before bot.py integration.")

if __name__ == "__main__":
    main()
