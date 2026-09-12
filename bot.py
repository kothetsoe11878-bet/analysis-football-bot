import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": CHANNEL_USERNAME,
            "text": text
        },
        timeout=30
    )

    response.raise_for_status()
    print("Message sent successfully.")

if __name__ == "__main__":
    send_message(
        "⚽ Analysis Football Bot\n\n"
        "✅ Bot connection test successful.\n\n"
        "Allowed Competitions:\n"
        "• EPL\n"
        "• La Liga\n"
        "• Serie A\n"
        "• Bundesliga\n"
        "• Ligue 1\n"
        "• UEFA Champions League"
    )
