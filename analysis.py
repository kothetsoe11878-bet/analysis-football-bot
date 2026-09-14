# Analysis Football Bot — Analysis Engine
# Fail-closed: no verified evidence = no betting pick.

from rules import validate_pick, NEVER_FORCE_PICK, NEVER_FABRICATE_DATA


def _has_value(value):
    return value not in (None, "", [], {})


def required_evidence_ok(data):
    """Require verified match data before analysis."""
    if not isinstance(data, dict):
        return False, "Invalid analysis data."

    for key in ("competition", "home", "away"):
        if not _has_value(data.get(key)):
            return False, f"Missing verified field: {key}"

    if data["competition"] not in {
        "EPL", "La Liga", "Serie A",
        "Bundesliga", "Ligue 1", "UCL"
    }:
        return False, "Competition is not allowed."

    return True, "OK"


def build_analysis_input(match, bt=None, current=None, news=None, odds=None):
    """
    Prepare only verified/available evidence for the analysis layer.
    Missing optional evidence is marked unknown; it is never invented.
    """
    ok, reason = required_evidence_ok(match)
    if not ok:
        raise RuntimeError(reason)

    return {
        "match": match,
        "bt": bt if isinstance(bt, dict) else {"status": "unknown"},
        "current": current if isinstance(current, dict) else {"status": "unknown"},
        "news": news if isinstance(news, dict) else {"status": "unknown"},
        "odds": odds if isinstance(odds, dict) else {"status": "unknown"},
    }


def make_pick(analysis):
    """
    Convert a completed, evidence-backed analysis into a validated pick.
    This function deliberately refuses to invent line, odds, or confidence.
    """
    if not isinstance(analysis, dict):
        return {"status": "PASS", "reason": "Invalid analysis result."}

    required = (
        "competition", "home", "away", "market",
        "line", "myanmar_odds", "strength"
    )

    if any(not _has_value(analysis.get(k)) for k in required):
        return {
            "status": "PASS",
            "reason": "Required verified betting information is incomplete."
        }

    valid, reason = validate_pick(analysis)
    if not valid:
        return {"status": "PASS", "reason": reason}

    return {
        "status": "PICK",
        "competition": analysis["competition"],
        "home": analysis["home"],
        "away": analysis["away"],
        "market": analysis["market"],
        "line": analysis["line"],
        "myanmar_odds": analysis["myanmar_odds"],
        "strength": analysis["strength"],
        "reason": analysis.get("reason", ""),
        "risk": analysis.get("risk", "Not specified"),
    }


def analyze_match(match, bt=None, current=None, news=None, odds=None):
    """
    Safe entry point for future Gemini integration.
    Gemini output must still pass make_pick() before Telegram publication.
    """
    evidence = build_analysis_input(
        match, bt=bt, current=current, news=news, odds=odds
    )

    # No automatic prediction is generated here.
    # A future Gemini result must be passed through make_pick().
    return {
        "status": "READY_FOR_GEMINI",
        "evidence": evidence,
    }
