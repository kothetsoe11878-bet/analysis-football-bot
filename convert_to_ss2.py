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
    name = name.replace("&", "and")

    name = re.sub(
        r"\b(fc|cf|afc|ac|sc|sv|vfb|fk)\b",
        "",
        name,
        flags=re.IGNORECASE,
    )

    aliases = {
        "manchester united": "man united",
        "manchester city": "man city",
        "tottenham hotspur": "tottenham",
        "wolverhampton wanderers": "wolves",
        "brighton and hove albion": "brighton",
        "west ham united": "west ham",
        "newcastle united": "newcastle",
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

        with open(
            file,
            encoding="utf-8-sig",
            newline=""
        ) as f:

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

        with open(
            file,
            encoding="utf-8-sig",
            newline=""
        ) as f:

            reader = csv.DictReader(f)

            for r in reader:

                # PINNACLE ONLY
                if r.get("bookmaker", "").strip().lower() != "pinnacle":
                    continue

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


def build_key(league, date, home, away):

    return (
        league,
        date,
        normalize_team(home),
        normalize_team(away),
    )


def calculate_body_result(home_goals, away_goals, selected_team, handicap):

    try:
        hg = float(home_goals)
        ag = float(away_goals)
        ah = float(handicap)
    except (ValueError, TypeError):
        return ""

    if selected_team == "HOME":
        adjusted = (hg - ag) + ah
    else:
        adjusted = (ag - hg) + ah

    if adjusted > 0:
        return "WIN"

    if adjusted < 0:
        return "LOSS"

    return "PUSH"


def build_matches(results, odds):

    odds_index = {}

    for odd in odds:

        key = build_key(
            odd["league"],
            odd["date"],
            odd["home_team"],
            odd["away_team"],
        )

        # One Pinnacle row per match/key
        if key not in odds_index:
            odds_index[key] = odd

    output = []

    for result in results:

        key = build_key(
            result["league"],
            result["date"],
            result["home_team"],
            result["away_team"],
        )

        odd = odds_index.get(key)

        if not odd:

            output.append({
                **result,
                "match_id_odds": "",
                "bookmaker": "",
                "market": "",
                "home_handicap": "",
                "home_price": "",
                "away_handicap": "",
                "away_price": "",
                "selected_team": "",
                "selected_handicap": "",
                "selected_price": "",
                "body_result": "",
                "odds_match": "NO_ODDS_MATCH",
            })

            continue

        # Current bridge keeps the home-side AH.
        # Selected team is HOME.
        selected_team = "HOME"
        selected_handicap = odd["home_handicap"]
        selected_price = odd["home_price"]

        body_result = calculate_body_result(
            result["home_goals"],
            result["away_goals"],
            selected_team,
            selected_handicap,
        )

        output.append({
            **result,
            "match_id_odds": odd["match_id_odds"],
            "bookmaker": odd["bookmaker"],
            "market": odd["market"],
            "home_handicap": odd["home_handicap"],
            "home_price": odd["home_price"],
            "away_handicap": odd["away_handicap"],
            "away_price": odd["away_price"],
            "selected_team": selected_team,
            "selected_handicap": selected_handicap,
            "selected_price": selected_price,
            "body_result": body_result,
            "odds_match": "MATCHED",
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
        "selected_team",
        "selected_handicap",
        "selected_price",
        "body_result",
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

    print("Loading Pinnacle odds only...")
    odds = load_odds()
    print(f"Pinnacle odds rows: {len(odds)}")

    print("Matching Results + Pinnacle AH...")

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

    wins = sum(
        1
        for r in combined
        if r["body_result"] == "WIN"
    )

    losses = sum(
        1
        for r in combined
        if r["body_result"] == "LOSS"
    )

    pushes = sum(
        1
        for r in combined
        if r["body_result"] == "PUSH"
    )

    print(f"Matched rows: {matched}")
    print(f"Unmatched rows: {unmatched}")
    print(f"Body WIN: {wins}")
    print(f"Body LOSS: {losses}")
    print(f"Body PUSH: {pushes}")

    save_output(combined)

    print("SS2 Pinnacle bridge completed.")


if __name__ == "__main__":
    main()
