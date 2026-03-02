import requests
import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

ENV_PATH = "/home/datascientest/cde/polar/.env"
load_dotenv(ENV_PATH)

TOKEN = os.getenv("POLAR_ACCESS_TOKEN")
USER_ID = os.getenv("POLAR_USER_ID")
BASE_URL = "https://www.polaraccesslink.com/v3"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json"
}

def create_transaction():
    r = requests.post(
        f"{BASE_URL}/users/{USER_ID}/exercise-transactions",
        headers=HEADERS
    )
    if r.status_code == 204:
        print("Aucune nouvelle séance disponible")
        return None
    elif r.status_code == 201:
        tid = r.json().get("transaction-id")
        print(f"Transaction créée : {tid}")
        return tid
    else:
        print(f"Erreur : {r.status_code} {r.text}")
        return None

def get_exercises(transaction_id):
    r = requests.get(
        f"{BASE_URL}/users/{USER_ID}/exercise-transactions/{transaction_id}",
        headers=HEADERS
    )
    return r.json().get("exercises", [])

def get_exercise_detail(exercise_url):
    r = requests.get(exercise_url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()
    return {}

def commit_transaction(transaction_id):
    requests.put(
        f"{BASE_URL}/users/{USER_ID}/exercise-transactions/{transaction_id}",
        headers=HEADERS
    )
    print(f"Transaction {transaction_id} commitée")

def write_to_influx(exercises):
    client = InfluxDBClient(
        url=os.getenv("INFLUX_URL"),
        token=os.getenv("INFLUX_TOKEN"),
        org=os.getenv("INFLUX_ORG")
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)

    for ex_url in exercises:
        ex = get_exercise_detail(ex_url)
        if not ex:
            continue

        exercise_id = str(ex.get("id", ""))
        start_time = ex.get("start-time")

        point = (
            Point("exercise")
            # --- dimensions (tags) ---
            .tag("exercise_id", exercise_id)   # clé unique anti-doublon
            .tag("user_id", USER_ID)
            .tag("sport", ex.get("sport", "unknown"))
            .tag("device", ex.get("device", {}).get("name", "unknown"))
            # --- métriques (fields) ---
            .field("duration_sec", ex.get("duration", 0))
            .field("calories", ex.get("calories", 0))
            .field("hr_avg", ex.get("heart-rate", {}).get("average", 0))
            .field("hr_max", ex.get("heart-rate", {}).get("maximum", 0))
            .field("distance_m", ex.get("distance", 0))
            # --- timestamp ---
            .time(start_time)
        )

        write_api.write(bucket=os.getenv("INFLUX_BUCKET"), record=point)
        print(f"✅ Écrit : {start_time} | {ex.get('sport')} | id={exercise_id}")

if __name__ == "__main__":
    tid = create_transaction()
    if tid:
        exercises = get_exercises(tid)
        write_to_influx(exercises)
        commit_transaction(tid)