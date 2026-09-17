import os
import requests


MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/{MODEL}"
)


def main():
    key = os.getenv("GEMINI_API_KEY")

    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    response = requests.get(
        URL,
        headers={
            "x-goog-api-key": key
        },
        timeout=30,
    )

    print("HTTP STATUS:", response.status_code)
    print("MODEL:", MODEL)
    print("RESPONSE:")
    print(response.text[:5000])

    response.raise_for_status()

    data = response.json()

    assert data.get("name") == f"models/{MODEL}"

    supported = data.get("supportedGenerationMethods", [])

    print("SUPPORTED METHODS:", supported)

    assert "generateContent" in supported

    print("MODEL DIAGNOSTIC: PASS")


if __name__ == "__main__":
    main()
