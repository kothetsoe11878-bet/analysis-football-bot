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

    replacements = {
        "manchester united fc": "manchester united",
        "manchester city fc": "manchester city",
        "tottenham hotspur fc": "tottenham hotspur",
        "west ham united fc": "west ham united",
        "newcastle united fc": "newcastle united",
        "aston villa fc": "aston villa",
        "nottingham forest fc": "nottingham forest",
        "brighton & hove albion": "brighton",
        "wolverhampton wanderers fc": "wolverhampton wanderers",
        "real madrid cf": "real madrid",
        "fc barcelona": "barcelona",
        "atletico madrid": "atlético madrid",
    }

    name = replacements.get(name, name)

    name = re.sub(r"\s+", " ", name)

    return name


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


def build_matches(results, odds):
    output = []

    for result in results:

        r_home = normalize_team(result["home_team"])
        r_away = normalize_team(result["away_team"])

        candidates = []

        for odd in odds:

            if odd["league"] != result["league"]:
                continue

            if odd["date"] != result["date"]:
                continue

            o_home = normalize_team(odd["home_team"])
            o_away = normalize_team(odd["away_team"])

            if r_home == o_home and r_away == o_away:
                candidates.append(odd)

        if candidates:
            for odd in candidates:
                output.append({
                    **result,
                    "match_id_odds": odd["match_id_odds"],
                    "bookmaker": odd["bookmaker"],
                    "market": odd["market"],
                    "home_handicap": odd["home_handicap"],
                    "home_price": odd["home_price"],
                    "away_handicap": odd["away_handicap"],
                    "away_price": odd["away_price"],
                    "odds_match": "MATCHED",
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
                "odds_match": "NO_ODDS_MATCH",
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

    with open(file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
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

    print("Matching results + odds...")
    combined = build_matches(results, odds)

    matched = sum(
        1 for r in combined
        if r["odds_match"] == "MATCHED"
    )

    print(f"Matched rows: {matched}")
    print(f"Unmatched rows: {len(combined) - matched}")

    save_output(combined)

    print("SS2 Data Bridge completed.")


if __name__ == "__main__":
    main()
