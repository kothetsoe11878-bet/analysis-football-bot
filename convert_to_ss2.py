import csv
import re
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path("data/results")
ODDS_DIR = Path("data/odds")
OUTPUT_DIR = Path("data/ss2")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LEAGUES = {
    "epl": "EPL",
    "la_liga": "La Liga",
    "serie_a": "Serie A",
    "bundesliga": "Bundesliga",
    "ligue_1": "Ligue 1",
}


def normalize_team(name):
    if not name:
        return ""

    name = name.lower().strip()

    # Remove common football club suffixes
    name = re.sub(
        r"\b(fc|cf|afc|ac|sc|sv|vfb|fk)\b",
        "",
        name,
        flags=re.IGNORECASE,
    )

    # Standard aliases
    aliases = {
        "manchester united": "man united",
        "manchester city": "man city",
        "tottenham hotspur": "tottenham",
        "wolverhampton wanderers": "wolves",
        "brighton and hove albion": "brighton",
        "brighton & hove albion": "brighton",
        "west ham united": "west ham",
        "newcastle united": "newcastle",
        "nottingham forest": "nottingham forest",
        "real madrid": "real madrid",
        "atletico madrid": "atletico madrid",
        "atletico de madrid": "atletico madrid",
        "fc barcelona": "barcelona",
        "internazionale": "inter",
        "inter milan": "inter",
        "ac milan": "milan",
        "paris saint-germain": "psg",
        "paris saint germain": "psg",
        "olympique lyonnais": "lyon",
        "olympique de marseille": "marseille",
        "borussia dortmund": "dortmund",
        "bayern munich": "bayern",
        "bayern munchen": "bayern",
    }

    name = name.replace("&", "and")
    name = re.sub(r"\s+", " ", name).strip()

    return aliases.get(name, name)


def date_key(value):
    if not value:
        return ""

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date().isoformat()
    except Exception:
        return value[:10]


def load_results():
    rows = []

    for file in RESULTS_DIR.glob("*_current.csv"):

        league_key = file.stem.replace("_current", "")
        league = LEAGUES.get(league_key)

        if not league:
            continue

        with open(file, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for r in reader:
                rows.append({
                    "league": league,
                    "match_id_result": r.get("match_id", ""),
                    "date": date_key(r.get("date", "")),
                    "status": r.get("status", ""),
                    "matchday": r.get("matchday", ""),
                    "home_team": r.get("home_team", ""),
                    "away_team": r.get("away_team", ""),
                    "home_goals": r.get("home_goals", ""),
                    "away_goals": r.get("away_goals", ""),
                    "winner": r.get("winner", ""),
                })

    return rows


def load_odds():
    rows = []

    for file in ODDS_DIR.glob("*_odds_current.csv"):

        league_key = file.stem.replace("_odds_current", "")
        league = LEAGUES.get(league_key)

        if not league:
            continue

        with open(file, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for r in reader:
                rows.append({
                    "league": league,
                    "match_id_odds": r.get("match_id", ""),
                    "date": date_key(r.get("commence_time", "")),
                    "home_team": r.get("home_team", ""),
                    "away_team": r.get("away_team", ""),
                    "bookmaker": r.get("bookmaker", ""),
                    "market": r.get("market", ""),
                    "home_handicap": r.get("home_handicap", ""),
                    "home_price": r.get("home_price", ""),
                    "away_handicap": r.get("away_handicap", ""),
                    "away_price": r.get("away_price", ""),
                })

    return rows


def build_match_key(league, date, home, away):
    return (
        league,
        date,
        normalize_team(home),
        normalize_team(away),
    )


def build_odds_index(odds):

    index = {}

    for odd in odds:

        key = build_match_key(
            odd["league"],
            odd["date"],
            odd["home_team"],
            odd["away_team"],
        )

        index.setdefault(key, []).append(odd)

    return index


def build_matches(results, odds):

    odds_index = build_odds_index(odds)

    output = []

    for result in results:

        key = build_match_key(
            result["league"],
            result["date"],
            result["home_team"],
            result["away_team"],
        )

        candidates = odds_index.get(key, [])

        if candidates:

            for odd in candidates:

                output.append({
                    **result,

                    "match_id_odds":
                        odd["match_id_odds"],

                    "bookmaker":
                        odd["bookmaker"],

                    "market":
                        odd["market"],

                    "home_handicap":
                        odd["home_handicap"],

                    "home_price":
                        odd["home_price"],

                    "away_handicap":
                        odd["away_handicap"],

                    "away_price":
                        odd["away_price"],

                    "odds_match":
                        "MATCHED",
                })

        else:

            output.append({
                **result,

                "match_id_odds": "",
                "bookmaker": "",
                "market": "",
                "home_handicap": "",
                "home_price": "",
                "away_handicap": "",
                "away_price": "",

                "odds_match":
                    "NO_ODDS_MATCH",
            })

    return output


def save_output(rows):

    file = OUTPUT_DIR / "ss2_bridge_current.csv"

    fields = [
        "league",
        "date",
        "status",
        "matchday",
        "home_team",
        "away_team",
        "home_goals",
        "away_goals",
        "winner",
        "match_id_result",
        "match_id_odds",
        "bookmaker",
        "market",
        "home_handicap",
        "home_price",
        "away_handicap",
        "away_price",
        "odds_match",
    ]

    with open(
        file,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(rows)

    print(f"Created: {file}")
    print(f"Rows: {len(rows)}")


def main():

    print("Loading results...")
    results = load_results()
    print(f"Results: {len(results)}")

    print("Loading odds...")
    odds = load_odds()
    print(f"Odds rows: {len(odds)}")

    print("Building match index...")
    print("Matching Results + Asian Handicap...")

    combined = build_matches(
        results,
        odds
    )

    matched = sum(
        1
        for r in combined
        if r["odds_match"] == "MATCHED"
    )

    unmatched = len(combined) - matched

    print(f"Matched rows: {matched}")
    print(f"Unmatched rows: {unmatched}")

    save_output(combined)

    print("SS2 Data Bridge completed.")


if __name__ == "__main__":
    main()
