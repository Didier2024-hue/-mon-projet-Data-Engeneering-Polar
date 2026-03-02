import requests
import os
from dotenv import load_dotenv

ENV_PATH = "/home/datascientest/cde/polar/.env"
load_dotenv(ENV_PATH)

TOKEN = os.getenv("POLAR_ACCESS_TOKEN")
USER_ID = os.getenv("POLAR_USER_ID")

# Enregistrer l'utilisateur
r = requests.post(
    "https://www.polaraccesslink.com/v3/users",
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    },
    json={"member-id": str(USER_ID)}
)
print(f"Register : {r.status_code} {r.text}")

# Récupérer le profil
r2 = requests.get(
    f"https://www.polaraccesslink.com/v3/users/{USER_ID}",
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json"
    }
)
print(f"Profil : {r2.status_code} {r2.text}")