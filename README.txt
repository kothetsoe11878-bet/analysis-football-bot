ANALYSIS FOOTBALL — GEMINI ANALYSIS MODULE

This module is intentionally separate from bot.py.
DO NOT modify bot.py while testing.

Upload/copy these files into the root of analysis-football-bot:
- gemini_analysis.py
- gemini_test.py
- .github/workflows/gemini-test.yml
- README.txt

Then GitHub Actions -> Gemini Analysis Module Test -> Run workflow.
Expected output: GEMINI MODULE TEST: PASS

GEMINI_API_KEY must already exist as a GitHub repository secret.
Never paste the secret into chat or source code.

Missing/weak/contradictory evidence => PASS.
The locked Asian Line -> Myanmar Odds mapping is preserved.
Do not connect to bot.py until this isolated test passes.
