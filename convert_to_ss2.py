import csv
import re
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path("data/results")
ODDS_DIR = Path("data/odds")
OUTPUT_DIR = Path("data/ss2")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RESULT_FILES = {
    "EPL": RESULTS_DIR / "epl_current.csv",
    "La_Liga": RESULTS_DIR / "la_liga_current.csv",
    "Serie_A": RESULTS_DIR / "serie_a_current.csv",
    "Bundesliga": RESULTS_DIR / "bundesliga_current.csv",
    "Ligue_1": RESULTS_DIR / "ligue_1_current.csv",
}

ODDS_FILES = {
    "EPL": ODDS_DIR / "epl_odds_current.csv",
    "La_Liga": ODDS_DIR / "la_liga_odds_current.csv",
    "Serie_A": ODDS_DIR / "serie_a_odds_current.csv",
    "Bundesliga": ODDS_DIR / "bundesliga_odds_current.csv",
    "Ligue_1": ODDS_DIR / "ligue_1_odds_current.csv",
}


# ---------------------------------------------------------
# TEAM NAME NORMALIZATION
# ---------------------------------------------------------

ALIASES = {
    # EPL
    "manchester united fc": "manchester united",
    "manchester city fc": "manchester city",
    "tottenham hotspur fc": "tottenham",
    "tottenham hotspur": "tottenham",
    "west ham united fc": "west ham",
    "wolverhampton wanderers fc": "wolves",
    "wolverhampton wanderers": "wolves",
    "brighton & hove albion fc": "brighton",
    "brighton and hove albion": "brighton",
    "nottingham forest fc": "nottingham forest",
    "newcastle united fc": "newcastle united",
    "crystal palace fc": "crystal palace",
    "aston villa fc": "aston villa",
    "afc bournemouth": "bournemouth",
    "ipswich town fc": "ipswich",
    "leicester city fc": "leicester city",
    "everton fc": "everton",
    "fulham fc": "fulham",
    "brentford fc": "brentford",
    "arsenal fc": "arsenal",
    "chelsea fc": "chelsea",
    "liverpool fc": "liverpool",

    # La Liga
    "fc barcelona": "barcelona",
    "barcelona": "barcelona",
    "real madrid cf": "real madrid",
    "real madrid": "real madrid",
    "atletico de madrid": "atletico madrid",
    "club atletico de madrid": "atletico madrid",
    "athletic club": "athletic bilbao",
    "athletic club bilbao": "athletic bilbao",
    "rcd espanyol": "espanyol",
    "rcd espanyol de barcelona": "espanyol",
    "rcd mallorca": "mallorca",
    "real betis balompie": "real betis",
    "real betis": "real betis",
    "real sociedad de futbol": "real sociedad",
    "real sociedad": "real sociedad",
    "villarreal cf": "villarreal",
    "sevilla fc": "sevilla",
    "rc celta": "celta vigo",
    "celta vigo": "celta vigo",
    "deportivo alaves": "alaves",
    "deportivo alaves sad": "alaves",
    "girona fc": "girona",
    "getafe cf": "getafe",
    "rayo vallecano de madrid": "rayo vallecano",
    "rayo vallecano": "rayo vallecano",
    "ca osasuna": "osasuna",
    "cd leganes": "leganes",
    "ud las palmas": "las palmas",
    "real valladolid cf": "valladolid",

    # Serie A
    "inter milan": "inter",
    "fc internazionale milano": "inter",
    "internazionale": "inter",
    "ac milan": "milan",
    "juventus fc": "juventus",
    "as roma": "roma",
    "ss lazio": "lazio",
    "ssc napoli": "napoli",
    "atalanta bc": "atalanta",
    "acf fiorentina": "fiorentina",
    "bologna fc 1909": "bologna",
    "torino fc": "torino",
    "genoa cfc": "genoa",
    "udinese calcio": "udinese",
    "hellas verona fc": "verona",
    "parma calcio 1913": "parma",
    "cagliari calcio": "cagliari",
    "como 1907": "como",
    "venezia fc": "venezia",
    "empoli fc": "empoli",
    "monza": "monza",
    "us lecce": "lecce",

    # Bundesliga
    "fc bayern munich": "bayern munich",
    "bayern munich": "bayern munich",
    "borussia dortmund": "dortmund",
    "bayer 04 leverkusen": "leverkusen",
    "rb leipzig": "leipzig",
    "eintracht frankfurt": "eintracht frankfurt",
    "sc freiburg": "freiburg",
    "vfb stuttgart": "stuttgart",
    "mainz 05": "mainz",
    "1. fc union berlin": "union berlin",
    "union berlin": "union berlin",
    "borussia monchengladbach": "monchengladbach",
    "borussia mönchengladbach": "monchengladbach",
    "fc augsburg": "augsburg",
    "sv werder bremen": "werder bremen",
    "werder bremen": "werder bremen",
    "tsg 1899 hoffenheim": "hoffenheim",
    "vfl wolfsburg": "wolfsburg",
    "fc heidenheim": "heidenheim",
    "fc st pauli": "st pauli",
    "holstein kiel": "holstein kiel",

    # Ligue 1
    "paris saint-germain fc": "psg",
    "paris saint-germain": "psg",
    "psg": "psg",
    "olympique de marseille": "marseille",
    "olympique lyonnais": "lyon",
    "as monaco fc": "monaco",
    "lille osc": "lille",
    "ogc nice": "nice",
    "rc lens": "lens",
    "stade rennais fc": "rennes",
    "stade brestois 29": "brest",
    "fc nantes": "nantes",
    "rc strasbourg alsace": "strasbourg",
    "montpellier hsc": "montpellier",
    "toulouse fc": "toulouse",
    "aj auxerre": "auxerre",
    "angers sco": "angers",
    "le havre ac": "le havre",
    "as saint-etienne": "saint etienne",
    "reims": "reims",
}


def normalize_team(name):
    if not name:
        return ""

    s = name.lower().strip()

    s = s.replace("&", "and")
    s = s.replace("’", "'")
    s = re.sub(r"\b(fc|cf|sc|afc|ac|bc|cfc|sad)\b", "", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    return ALIASES.get(s, s)


def get_date(value):
    if not value:
        return ""

    value = value.strip()

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date().isoformat()
    except Exception:
        return value[:10]


# ---------------------------------------------------------
# HANDICAP / BODY RESULT
# ---------------------------------------------------------

def quarter_parts(handicap):
    """
    -0.25 -> [-0.0, -0.5]
    -0.75 -> [-0.5, -1.0]
     0.25 -> [0.0, 0.5]
     0.75 -> [0.5, 1.0]
    """

    h = float(handicap)

    if abs((h * 4) % 2) == 1:
        if h > 0:
            return [h - 0.25, h + 0.25]
        else:
            return [h + 0.25, h - 0.25]

    return [h]


def settle_single(goal_diff, handicap):
    adjusted = goal_diff + handicap

    if adjusted > 0:
        return "WIN"

    if adjusted < 0:
        return "LOSS"

    return "PUSH"


def settle_body(goal_diff, handicap):
    parts = quarter_parts(handicap)

    results = [settle_single(goal_diff, h) for h in parts]

    if len(results) == 1:
        return results[0]

    # Quarter handicap
    if results[0] == "WIN" and results[1] == "WIN":
        return "WIN"

    if results[0] == "LOSS" and results[1] == "LOSS":
        return "LOSS"

    if "WIN" in results and "PUSH" in results:
        return "HALF_WIN"

    if "LOSS" in results and "PUSH" in results:
        return "HALF_LOSS"

    return "PUSH"


def myanmar_handicap(handicap):
    """
    Convert Asian handicap number to Myanmar notation.

    Examples:
    0.0   -> D
    0.25  -> L-50
    0.5   -> L-100
    0.75  -> 1+50
    1.0   -> 1D
    1.25  -> 1-50
    1.5   -> 1-100
    1.75  -> 2+50
    2.0   -> 2D
    """

    h = abs(float(handicap))
    whole = int(h)
    frac = round(h - whole, 2)

    if frac == 0:
        return f"{whole}D" if whole > 0 else "D"

    if frac == 0.25:
        if whole == 0:
            return "L-50"
        return f"{whole}L-50"

    if frac == 0.5:
        if whole == 0:
            return "L-100"
        return f"{whole}L-100"

    if frac == 0.75:
        return f"{whole + 1}+50"

    return str(h)


def arrow_for_team(team_handicap):
    h = float(team_handicap)

    if h < 0:
        return "↑"

    if h > 0:
        return ""

    return ""


# ---------------------------------------------------------
# LOAD RESULTS
# ---------------------------------------------------------

def load_results():
    results = []

    for league, path in RESULT_FILES.items():

        if not path.exists():
            print(f"Missing results file: {path}")
            continue

        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                if not row.get("home_team") or not row.get("away_team"):
                    continue

                if row.get("home_goals") in ("", None):
                    continue

                if row.get("away_goals") in ("", None):
                    continue

                try:
                    hg = int(row["home_goals"])
                    ag = int(row["away_goals"])
                except Exception:
                    continue

                results.append({
                    "league": league,
                    "match_id": row.get("match_id", ""),
                    "date": get_date(row.get("date", "")),
                    "home_team": row.get("home_team", ""),
                    "away_team": row.get("away_team", ""),
                    "home_norm": normalize_team(row.get("home_team", "")),
                    "away_norm": normalize_team(row.get("away_team", "")),
                    "home_goals": hg,
                    "away_goals": ag,
                })

    return results


# ---------------------------------------------------------
# LOAD PINNACLE ODDS
# ---------------------------------------------------------

def load_pinnacle_odds():
    odds = []

    for league, path in ODDS_FILES.items():

        if not path.exists():
            print(f"Missing odds file: {path}")
            continue

        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:

                bookmaker = row.get("bookmaker", "").strip().lower()

                if bookmaker != "pinnacle":
                    continue

                if row.get("home_handicap") in ("", None):
                    continue

                try:
                    home_handicap = float(row["home_handicap"])
                    home_price = float(row["home_price"])
                    away_handicap = float(row["away_handicap"])
                    away_price = float(row["away_price"])
                except Exception:
                    continue

                odds.append({
                    "league": league,
                    "match_id": row.get("match_id", ""),
                    "date": get_date(row.get("commence_time", "")),
                    "home_team": row.get("home_team", ""),
                    "away_team": row.get("away_team", ""),
                    "home_norm": normalize_team(row.get("home_team", "")),
                    "away_norm": normalize_team(row.get("away_team", "")),
                    "home_handicap": home_handicap,
                    "home_price": home_price,
                    "away_handicap": away_handicap,
                    "away_price": away_price,
                })

    return odds


# ---------------------------------------------------------
# MATCH RESULTS + ODDS
# ---------------------------------------------------------

def build_bridge(results, odds):

    # Index odds by:
    # league + date + home + away
    odds_index = {}

    for odd in odds:
        key = (
            odd["league"],
            odd["date"],
            odd["home_norm"],
            odd["away_norm"],
        )

        odds_index[key] = odd

    output = []

    matched = 0
    unmatched = 0

    body_win = 0
    body_loss = 0
    body_push = 0
    body_half_win = 0
    body_half_loss = 0

    for result in results:

        key = (
            result["league"],
            result["date"],
            result["home_norm"],
            result["away_norm"],
        )

        odd = odds_index.get(key)

        if not odd:
            unmatched += 1
            continue

        matched += 1

        hg = result["home_goals"]
        ag = result["away_goals"]

        # -------------------------------------------------
        # HOME TEAM ROW
        # -------------------------------------------------

        home_ah = odd["home_handicap"]
        home_body = settle_body(hg - ag, home_ah)

        if home_body == "WIN":
            body_win += 1
        elif home_body == "LOSS":
            body_loss += 1
        elif home_body == "PUSH":
            body_push += 1
        elif home_body == "HALF_WIN":
            body_half_win += 1
        elif home_body == "HALF_LOSS":
            body_half_loss += 1

        output.append({
            "league": result["league"],
            "date": result["date"],
            "match_id": result["match_id"],
            "team": result["home_team"],
            "opponent": result["away_team"],
            "h_a": "H",
            "arrow": arrow_for_team(home_ah),
            "ah": abs(home_ah),
            "myanmar_ah": myanmar_handicap(home_ah),
            "odds": odd["home_price"],
            "score": f"{hg}-{ag}",
            "body_result": home_body,
            "source": "Pinnacle",
        })

        # -------------------------------------------------
        # AWAY TEAM ROW
        # -------------------------------------------------

        away_ah = -odd["home_handicap"]
        away_body = settle_body(ag - hg, away_ah)

        if away_body == "WIN":
            body_win += 1
        elif away_body == "LOSS":
            body_loss += 1
        elif away_body == "PUSH":
            body_push += 1
        elif away_body == "HALF_WIN":
            body_half_win += 1
        elif away_body == "HALF_LOSS":
            body_half_loss += 1

        output.append({
            "league": result["league"],
            "date": result["date"],
            "match_id": result["match_id"],
            "team": result["away_team"],
            "opponent": result["home_team"],
            "h_a": "A",
            "arrow": arrow_for_team(away_ah),
            "ah": abs(away_ah),
            "myanmar_ah": myanmar_handicap(away_ah),
            "odds": odd["away_price"],
            "score": f"{hg}-{ag}",
            "body_result": away_body,
            "source": "Pinnacle",
        })

    return (
        output,
        matched,
        unmatched,
        body_win,
        body_loss,
        body_push,
        body_half_win,
        body_half_loss,
    )


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

def save_bridge(rows):

    filename = OUTPUT_DIR / "ss2_bridge_current.csv"

    fields = [
        "league",
        "date",
        "match_id",
        "team",
        "opponent",
        "h_a",
        "arrow",
        "ah",
        "myanmar_ah",
        "odds",
        "score",
        "body_result",
        "source",
    ]

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for row in rows:
            writer.writerow(row)

    print(f"Created: {filename}")
    print(f"Rows: {len(rows)}")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("Loading results...")
    results = load_results()
    print(f"Results: {len(results)}")

    print("Loading Pinnacle odds only...")
    odds = load_pinnacle_odds()
    print(f"Pinnacle odds rows: {len(odds)}")

    print("Matching Results + Pinnacle AH...")

    (
        rows,
        matched,
        unmatched,
        body_win,
        body_loss,
        body_push,
        body_half_win,
        body_half_loss,
    ) = build_bridge(results, odds)

    print(f"Matched matches: {matched}")
    print(f"Unmatched results: {unmatched}")

    print(f"Body WIN: {body_win}")
    print(f"Body LOSS: {body_loss}")
    print(f"Body PUSH: {body_push}")
    print(f"Body HALF WIN: {body_half_win}")
    print(f"Body HALF LOSS: {body_half_loss}")

    save_bridge(rows)

    print("SS2 Pinnacle bridge completed")


if __name__ == "__main__":
    main()
