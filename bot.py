import os
from datetime import datetime, timezone, timedelta

import requests


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

MMT = timezone(timedelta(hours=6, minutes=30))

ALLOWED_LEAGUES = {
    "EPL": "English Premier League",
    "La Liga": "La Liga",
    "Serie A": "Serie A",
    "Bundesliga": "Bundesliga",
    "Ligue 1": "Ligue 1",
    "UCL": "UEFA Champions League",
}


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": CHANNEL_USERNAME,
            "text": text,
        },
        timeout=30,
    )

    response.raise_for_status()


def get_mmt_time():
    return datetime.now(timezone.utc).astimezone(MMT)


def build_status_message():
    now = get_mmt_time()

    lines = [
        "⚽ ANALYSIS FOOTBALL BOT",
        "",
        "🤖 System Status: ONLINE",
        f"🕐 MMT: {now.strftime('%Y-%m-%d %I:%M %p')}",
        "",
        "🔒 ALLOWED COMPETITIONS",
    ]

    for short_name, full_name in ALLOWED_LEAGUES.items():
        lines.append(f"• {short_name} — {full_name}")

    lines.extend([
        "",
        "📊 Analysis Rules",
        "• BT is used as a historical filter",
        "• Current information must be verified",
        "• No fake news or fabricated odds",
        "• PASS is allowed",
        "• No guaranteed profit",
        "",
        "🔒 Prediction Lock",
        "Final prediction will be locked at 6:00 PM MMT.",
        "",
        "📌 Next Stage",
        "Fixture data + Gemini analysis will be connected.",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    send_message(build_status_message())
    print("Analysis Football Bot executed successfully.")
