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
            "note": "No usable football evidence supplied."
        }
    }

    result = analyze_match(test_match)

    print("=== FAIL-CLOSED TEST ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    assert result["status"] == "PASS"
    assert result["strength"] == "PASS"

    print("FAIL-CLOSED TEST: PASS")


if __name__ == "__main__":
    main()
