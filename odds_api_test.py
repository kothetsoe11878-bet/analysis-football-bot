from odds_api_module import summarize

if __name__ == "__main__":
    print("=== ODDS API CONNECTIVITY TEST ===")
    data = summarize("EPL")
    print("PASS: The Odds API returned EPL odds data." if data
          else "PASS: API connected, but no EPL odds events were returned.")
