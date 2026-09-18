import json
import os
import time
import requests


GEMINI_MODEL = "gemini-3.6-flash"

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/"
    f"models/{GEMINI_MODEL}:generateContent"
)


ALLOWED_COMPETITIONS = {
    "EPL",
    "La Liga",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
    "UCL",
}


# LOCKED: Asian Line -> Myanmar Odds
ASIAN_TO_MYANMAR = {
    0.0: "D",
    0.25: "L-50",
    0.5: "L-100",
    0.75: "1+50",
    1.0: "1D",
    1.25: "1-50",
    1.5: "1-100",
    1.75: "2+50",
    2.0: "2D",
    2.25: "2-50",
    2.5: "2-100",
    2.75: "3+50",
    3.0: "3D",
    3.25: "3-50",
    3.5: "3-100",
    3.75: "4+50",
    4.0: "4D",
    4.25: "4-50",
    4.5: "4-100",
    5.0: "5D",
}


RULES = """
You are the Analysis Football Gemini module.

1. Analyze only EPL, La Liga, Serie A, Bundesliga, Ligue 1, UCL.
2. Use only supplied evidence.
3. Never invent injuries, lineups, odds, form, xG, H2H,
   news, statistics, market movement or any other facts.
4. Insufficient, weak or contradictory evidence => PASS.
5. Never alter the supplied Asian line.
6. Never alter the supplied Myanmar odds.
7. Keep Asian line and Myanmar odds paired exactly.
8. Never promise profit.
9. Never force a PICK.
10. Return JSON only.
"""


def validate_input(match):
    required = (
        "competition",
        "home",
        "away",
        "market",
        "line",
        "myanmar_odds",
    )

    for key in required:
        if match.get(key) in (None, ""):
            return False, f"Missing required field: {key}"

    if match["competition"] not in ALLOWED_COMPETITIONS:
        return False, "Competition is outside the allowed six."

    if match["market"] not in {"OU", "AH"}:
        return False, "Market must be OU or AH."

    if not isinstance(match.get("evidence"), dict):
        return False, "Evidence must be a non-empty object."

    if not match["evidence"]:
        return False, "Evidence must be a non-empty object."

    return True, "OK"


def _json(text):
    text = text.strip()

    if text.startswith("```"):
        text = "\n".join(
            line
            for line in text.splitlines()
            if not line.strip().startswith("```")
        ).strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])

        raise


def _call_gemini(payload, api_key):

    retry_statuses = {
        429,
        500,
        502,
        503,
        504,
    }

    max_attempts = 4
    delays = [5, 10, 20]

    for attempt in range(max_attempts):

        try:
            response = requests.post(
                GEMINI_URL,
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )

            if response.status_code in retry_statuses:

                if attempt < max_attempts - 1:

                    delay = delays[attempt]

                    print(
                        f"Gemini temporary HTTP "
                        f"{response.status_code}. "
                        f"Retry {attempt + 1}/3 "
                        f"in {delay}s..."
                    )

                    time.sleep(delay)
                    continue

                raise RuntimeError(
                    "Gemini API temporary error after "
                    f"{max_attempts} attempts: "
                    f"HTTP {response.status_code}: "
                    f"{response.text[:1000]}"
                )

            response.raise_for_status()

            return response.json()

        except requests.RequestException as error:

            if attempt < max_attempts - 1:

                delay = delays[attempt]

                print(
                    f"Gemini request error: {error}. "
                    f"Retry {attempt + 1}/3 "
                    f"in {delay}s..."
                )

                time.sleep(delay)
                continue

            raise RuntimeError(
                "Gemini request failed after "
                f"{max_attempts} attempts: {error}"
            ) from error

    raise RuntimeError("Gemini request failed.")


def analyze_match(match):

    ok, reason = validate_input(match)

    if not ok:

        return {
            "status": "PASS",
            "reason": reason,
            "competition": match.get("competition"),
            "home": match.get("home"),
            "away": match.get("away"),
            "market": match.get("market"),
            "line": match.get("line"),
            "myanmar_odds": match.get("myanmar_odds"),
            "strength": "PASS",
        }

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set."
        )

    prompt = {
        "task": (
            "Analyze this football match using only "
            "the supplied evidence."
        ),
        "match": match,
        "required_output_fields": [
            "status",
            "competition",
            "home",
            "away",
            "market",
            "line",
            "myanmar_odds",
            "strength",
            "analysis_mm",
            "risk_mm",
            "final_pick_mm",
            "evidence_used",
        ],
        "status_values": [
            "PICK",
            "PASS",
        ],
        "strength_values": [
            "Strong",
            "Good",
            "Moderate",
            "PASS",
        ],
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            RULES
                            + "\n\nINPUT:\n"
                            + json.dumps(
                                prompt,
                                ensure_ascii=False,
                            )
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        },
    }

    data = _call_gemini(
        payload,
        api_key
    )

    try:

        text = (
            data["candidates"][0]
            ["content"]["parts"][0]["text"]
        )

    except (KeyError, IndexError, TypeError) as error:

        raise RuntimeError(
            f"Unexpected Gemini response: {data}"
        ) from error

    output = _json(text)

    # SECURITY LOCK
    # Gemini cannot change these fields.
    locked_fields = (
        "competition",
        "home",
        "away",
        "market",
        "line",
        "myanmar_odds",
    )

    for key in locked_fields:
        output[key] = match[key]

    output.setdefault(
        "status",
        "PASS"
    )

    output.setdefault(
        "strength",
        "PASS"
    )

    output.setdefault(
        "analysis_mm",
        ""
    )

    output.setdefault(
        "risk_mm",
        ""
    )

    output.setdefault(
        "final_pick_mm",
        ""
    )

    output.setdefault(
        "evidence_used",
        []
    )

    if output["status"] == "PASS":
        output["strength"] = "PASS"

    if output["status"] not in {
        "PICK",
        "PASS",
    }:

        output["status"] = "PASS"
        output["strength"] = "PASS"

    if output["strength"] not in {
        "Strong",
        "Good",
        "Moderate",
        "PASS",
    }:

        output["status"] = "PASS"
        output["strength"] = "PASS"

    return output


def run_connection_test():

    test_match = {
        "competition": "EPL",
        "home": "TEST HOME",
        "away": "TEST AWAY",
        "market": "OU",
        "line": 2.5,
        "myanmar_odds": "L-100",
        "evidence": {
            "note": (
                "Connection test only. "
                "No real football facts."
            )
        },
    }

    output = analyze_match(
        test_match
    )

    assert output["status"] == "PASS"
    assert output["line"] == 2.5
    assert output["myanmar_odds"] == "L-100"

    return output
