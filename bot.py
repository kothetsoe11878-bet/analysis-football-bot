import os
import requests
from datetime import datetime, timezone, timedelta

FDO_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

MMT = timezone(timedelta(hours=6, minutes=30))

COMPETITIONS = {
    "PL": "EPL",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "CL": "UCL",
}


def get_mmt_date():
    return datetime.now(MMT).strftime("%Y-%m-%d")


def test_competition(code, name):
    today = get_mmt_date()

    url = f"https://api.football-data.org/v4/competitions/{code}/matches"

    headers = {
        "X-Auth-Token": FDO_API_KEY,
        "Accept": "application/json",
    }

    params = {
        "season": 2026,
        "dateFrom": today,
        "dateTo": today,
    }

    print("")
    print("=" * 50)
    print(f"{name} ({code})")
    print("=" * 50)

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    print("HTTP Status:", response.status_code)

    try:
        data = response.json()
    except ValueError:
        print("Invalid JSON response")
        print(response.text[:500])
        return False

    if response.status_code != 200:
        print("API ERROR:")
        print(data)
        return False

    matches = data.get("matches", [])

    print("API result count:", len(matches))

    for match in matches:
        home = match.get("homeTeam", {}).get("name")
        away = match.get("awayTeam", {}).get("name")
        utc_date = match.get("utcDate")
        status = match.get("status")

        print(
            f"{utc_date} | {status} | "
            f"{home} vs {away}"
        )

    print(f"SUCCESS: {name}")

    return True


def main():

    print("==========================================")
    print("ANALYSIS FOOTBALL - FDO API TEST")
    print("==========================================")

    if not FDO_API_KEY:
        raise RuntimeError(
            "FOOTBALL_DATA_API_KEY is missing"
        )

    print("MMT Date:", get_mmt_date())
    print("Testing FDO 2026/27 access...")

    results = {}

    for code, name in COMPETITIONS.items():
        results[name] = test_competition(code, name)

    print("")
    print("==========================================")
    print("FINAL FDO ACCESS REPORT")
    print("==========================================")

    for name, success in results.items():
        if success:
            print(f"OK   : {name}")
        else:
            print(f"FAIL : {name}")

    print("")
    print("FDO API test completed.")


if __name__ == "__main__":
    main()
