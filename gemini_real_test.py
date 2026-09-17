from gemini_analysis import analyze_match


def main():
    match = {
        "competition": "EPL",
        "home": "Brentford",
        "away": "Chelsea",
        "market": "AH",
        "line": 0.25,
        "myanmar_odds": "L-50",

        "evidence": {
            "fixture": {
                "date": "2026-09-18",
                "kickoff": "20:00 BST",
                "venue": "Gtech Community Stadium"
            },

            "recent_form": {
                "Brentford": [
                    "Brentford 3-0 Tottenham",
                    "Leeds 1-1 Brentford",
                    "Brentford 1-1 Sunderland",
                    "Bournemouth 2-2 Brentford"
                ],
                "Chelsea": [
                    "Fulham 2-3 Chelsea",
                    "Chelsea 4-3 Brighton",
                    "Arsenal 2-1 Chelsea",
                    "Chelsea 2-2 Hull City"
                ]
            },

            "betting_evidence": {
                "source_line": "+0.25",
                "source_market": "Asian Handicap",
                "source_pick": "Brentford +0.25"
            },

            "source_note": (
                "Only the evidence supplied in this test may be used. "
                "Do not add injuries, lineups, xG, H2H, odds movement, "
                "or other facts unless supplied here."
            )
        }
    }

    result = analyze_match(match)

    print("========================================")
    print("GEMINI REAL MATCH TEST")
    print("========================================")
    print("Status       :", result.get("status"))
    print("Competition  :", result.get("competition"))
    print("Match        :", result.get("home"), "vs", result.get("away"))
    print("Market       :", result.get("market"))
    print("Line         :", result.get("line"))
    print("Myanmar Odds :", result.get("myanmar_odds"))
    print("Strength     :", result.get("strength"))
    print("Analysis     :", result.get("analysis_mm"))
    print("Risk         :", result.get("risk_mm"))
    print("Final Pick   :", result.get("final_pick_mm"))
    print("Evidence     :", result.get("evidence_used"))
    print("========================================")

    # Critical safety checks
    assert result["competition"] == "EPL"
    assert result["home"] == "Brentford"
    assert result["away"] == "Chelsea"
    assert result["market"] == "AH"

    # Line/Odds MUST NEVER change
    assert result["line"] == 0.25
    assert result["myanmar_odds"] == "L-50"

    assert result["status"] in {"PICK", "PASS"}
    assert result["strength"] in {
        "Strong",
        "Good",
        "Moderate",
        "PASS"
    }

    print("========================================")
    print("REAL MATCH TEST: PASS")
    print("========================================")


if __name__ == "__main__":
    main()
