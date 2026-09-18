import json
from gemini_analysis import analyze_match


def test_case(line, myanmar_odds):
    test_match = {
        "competition": "EPL",
        "home": "Test Home FC",
        "away": "Test Away FC",
        "market": "OU",
        "line": line,
        "myanmar_odds": myanmar_odds,
        "evidence": {
            "recent_home_matches": ["2-1", "1-1", "3-1"],
            "recent_away_matches": ["0-1", "1-1", "0-2"],
            "instruction": (
                "The supplied line and Myanmar odds are LOCKED. "
                "Never change them."
            )
        }
    }

    result = analyze_match(test_match)

    assert result["line"] == line
    assert result["myanmar_odds"] == myanmar_odds
    assert result["competition"] == "EPL"
    assert result["market"] == "OU"

    return result


def main():
    cases = [
        (2.5, "L-100"),
        (2.25, "2-50"),
        (2.75, "3+50"),
        (3.0, "3D"),
    ]

    for line, odds in cases:
        result = test_case(line, odds)
        print(
            f"LOCK TEST PASS: "
            f"{line} | {odds} | status={result['status']}"
        )

    print("MYANMAR ODDS LOCK TEST: PASS")


if __name__ == "__main__":
    main()
