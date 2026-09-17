import json
from gemini_analysis import analyze_match


def main():
    test_match = {
        "competition": "EPL",
        "home": "Test Home FC",
        "away": "Test Away FC",
        "market": "OU",
        "line": 2.5,
        "myanmar_odds": "L-100",
        "evidence": {
            "recent_home_matches": ["2-1", "1-1", "3-1", "2-0", "1-2"],
            "recent_away_matches": ["0-1", "1-1", "0-2", "2-1", "1-0"],
            "note": (
                "Synthetic test inputs only. Do not invent injuries, "
                "lineups, xG, H2H, odds movement, or other facts."
            )
        }
    }

    result = analyze_match(test_match)

    print("=== GEMINI REAL MATCH STRUCTURE TEST ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    required = [
        "status", "competition", "home", "away", "market", "line",
        "myanmar_odds", "strength", "analysis_mm", "risk_mm",
        "final_pick_mm", "evidence_used"
    ]

    for key in required:
        assert key in result, f"Missing output field: {key}"

    assert result["competition"] == test_match["competition"]
    assert result["home"] == test_match["home"]
    assert result["away"] == test_match["away"]
    assert result["market"] == test_match["market"]
    assert result["line"] == test_match["line"]
    assert result["myanmar_odds"] == test_match["myanmar_odds"]

    assert result["status"] in {"PICK", "PASS"}
    assert result["strength"] in {"Strong", "Good", "Moderate", "PASS"}

    if result["status"] == "PASS":
        assert result["strength"] == "PASS"

    print("REAL MATCH STRUCTURE TEST: PASS")


if __name__ == "__main__":
    main()
