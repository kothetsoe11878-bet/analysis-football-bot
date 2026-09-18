import json
from gemini_analysis import analyze_match


def main():
    test_match = {
        "competition": "EPL",
        "home": "Arsenal",
        "away": "Chelsea",
        "market": "OU",
        "line": 2.5,
        "myanmar_odds": "L-100",
        "evidence": {
            "recent_home_results": [
                "2-0",
                "3-1",
                "1-1",
                "2-1",
                "3-0"
            ],
            "recent_away_results": [
                "1-1",
                "0-2",
                "2-1",
                "1-0",
                "1-2"
            ],
            "important_note": (
                "These are test results only. "
                "Do not invent injuries, lineups, xG, H2H "
                "or other information."
            )
        }
    }

    result = analyze_match(test_match)

    print("=== GEMINI FINAL MODULE TEST ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # Locked fields
    assert result["competition"] == "EPL"
    assert result["home"] == "Arsenal"
    assert result["away"] == "Chelsea"
    assert result["market"] == "OU"
    assert result["line"] == 2.5
    assert result["myanmar_odds"] == "L-100"

    # Valid status
    assert result["status"] in {"PICK", "PASS"}

    # Valid strength
    assert result["strength"] in {
        "Strong",
        "Good",
        "Moderate",
        "PASS"
    }

    print("GEMINI FINAL MODULE TEST: PASS")


if __name__ == "__main__":
    main()
