import requests

url = "http://10.109.28.102:8000/v1/chat/completions"

payload = {
    "model": "sonatrach-IA",
    "messages": [
        {
            "role": "user",
            "content": "bonjour"
        }
    ],
    "max_tokens": 50
}

try:
    response = requests.post(
        url,
        json=payload,
        timeout=60
    )

    print("STATUS :", response.status_code)
    print("REPONSE :")
    print(response.text)

except Exception as e:
    print("ERREUR :", type(e).__name__)
    print(e)