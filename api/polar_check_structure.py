import requests
import os
from dotenv import load_dotenv
import json

ENV_PATH = "/home/datascientest/cde/polar/.env"
load_dotenv(ENV_PATH)

TOKEN = os.getenv("POLAR_ACCESS_TOKEN")
USER_ID = os.getenv("POLAR_USER_ID")
BASE_URL = "https://www.polaraccesslink.com/v3"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json"
}

# Créer une transaction
r = requests.post(
    f"{BASE_URL}/users/{USER_ID}/exercise-transactions",
    headers=HEADERS
)
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2))

# Corrige le script pour gérer le 204
if r.status_code == 204:
    print("Aucune nouvelle séance — 204 No Content")
elif r.status_code == 201:
    print(json.dumps(r.json(), indent=2))
else:
    print(f"Erreur : {r.status_code} {r.text}")
