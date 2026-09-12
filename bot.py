import os
from datetime import datetime, timezone, timedelta

import requests


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

MMT = timezone(timedelta(hours=6, minutes=30))


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


def create_user_output():
    now = get_mmt_time()

    # User-facing message only.
    # Internal rules are NOT displayed in Telegram.

    return (
        "⚽ ANALYSIS FOOTBALL\n\n"
        "📅 Football Analysis System\n"
        f"🕐 {now.strftime('%d %b %Y | %I:%M %p')} MMT\n\n"
        "🔄 System is ready.\n\n"
        "📊 Match data and analysis will be published here."
    )


if __name__ == "__main__":
    message = create_user_output()
    send_message(message)
    print("User-facing message sent successfully.")
