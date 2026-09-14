# Analysis Football Bot — Core Rules
# MMT = Myanmar Standard Time (UTC+6:30)

from datetime import datetime, timezone, timedelta

MMT = timezone(timedelta(hours=6, minutes=30))

ALLOWED_COMPETITIONS = {
    "PL": "EPL",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "CL": "UCL",
}

T1_HOUR, T1_MINUTE = 10, 0
FINAL_HOUR, FINAL_MINUTE = 18, 0
RESULT_HOUR, RESULT_MINUTE = 9, 0

T1_MAX_PICKS = 12
FINAL_MAX_PICKS = 4
UCL_T1_MAX_PICKS = 5
UCL_FINAL_MAX_PICKS = 2

ALLOW_PASS = True
NEVER_FORCE_PICK = True
NEVER_FABRICATE_DATA = True
NO_GUARANTEED_PROFIT = True
LOCK_FINAL_PREDICTION = True


def now_mmt():
    return datetime.now(MMT)


def is_allowed_competition(code: str) -> bool:
    return code in ALLOWED_COMPETITIONS


def competition_name(code: str) -> str:
    return ALLOWED_COMPETITIONS.get(code, "UNKNOWN")


def workflow_stage(now=None) -> str:
    now = now or now_mmt()
    total = now.hour * 60 + now.minute
    if total >= FINAL_HOUR * 60 + FINAL_MINUTE:
        return "FINAL_6PM"
    if total >= T1_HOUR * 60 + T1_MINUTE:
        return "T1_10AM"
    return "RESULT_REVIEW_9AM"


def validate_pick(pick: dict):
    required = (
        "competition", "home", "away", "market",
        "line", "myanmar_odds", "strength"
    )
    for key in required:
        if pick.get(key) in (None, ""):
            return False, f"Missing required field: {key}"

    if pick["competition"] not in ALLOWED_COMPETITIONS.values():
        return False, "Competition is outside the allowed six."

    if pick["strength"] not in {"Strong", "Good", "Moderate", "PASS"}:
        return False, "Invalid strength."

    if pick["market"] not in {"OU", "AH"}:
        return False, "Invalid market."

    return True, "OK"
