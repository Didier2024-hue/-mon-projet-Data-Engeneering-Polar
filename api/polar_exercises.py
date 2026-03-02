import requests
import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

ENV_PATH = "/home/datascientest/cde/polar/.env"
load_dotenv(ENV_PATH)

TOKEN = os.getenv("POLAR_ACCESS_TOKEN")
USER_ID = os.getenv("POLAR_USER_ID")
INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

# 1. Créer une transaction exercices
r = requests.post(
    f"https://www.polaraccesslink.com/v3/users/{USER_ID}/exercise-transactions",
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json"
    }
)
print(f"Transaction : {r.status_code} {r.text}")

if r.status_code == 201:
    transaction_id = r.json().get("transaction-id")
    
    # 2. Récupérer la liste des exercices
    r2 = requests.get(
        f"https://www.polaraccesslink.com/v3/users/{USER_ID}/exercise-transactions/{transaction_id}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json"
        }
    )
    print(f"Exercices : {r2.status_code} {r2.text}")