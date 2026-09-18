from gemini_analysis import ASIAN_TO_MYANMAR


EXPECTED = {
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


def main():
    assert ASIAN_TO_MYANMAR == EXPECTED

    for line, odds in EXPECTED.items():
        assert ASIAN_TO_MYANMAR[line] == odds
        print(f"PASS: {line} | {odds}")

    print("MYANMAR ODDS LOCAL TEST: PASS")


if __name__ == "__main__":
    main()
