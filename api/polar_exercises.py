#!/usr/bin/env python3
"""
Récupération des nouvelles séances Polar via AccessLink
- URL validée : /users/{USER_ID}/exercise-transactions
- Sauvegarde JSON dans data/extracted/
- Ingestion dans InfluxDB
"""
import json
import requests
import os
from pathlib import Path
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

ENV_PATH = Path.home() / "cde/polar/.env"
load_dotenv(ENV_PATH)

TOKEN    = os.getenv("POLAR_ACCESS_TOKEN")
USER_ID  = os.getenv("POLAR_USER_ID")
BASE_URL = f"https://www.polaraccesslink.com/v3/users/{USER_ID}"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json"
}

DATA_DIR = Path.home() / "cde/polar/data/extracted"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SPORT_MAPPING = {
    "RUNNING":              "Running",
    "CYCLING":              "Cycling",
    "WALKING":              "Walking",
    "MOUNTAIN_BIKING":      "Mountain_Biking",
    "SKIING":               "Skiing",
    "STRENGTH_TRAINING":    "Strength_Training",
    "FITNESS_DANCING":      "Fitness_Dancing",
    "AEROBICS":             "Aerobics",
    "SWIMMING":             "Swimming",
    "POOL_SWIMMING":        "Pool_Swimming",
    "HIKING":               "Hiking",
    "TREADMILL_RUNNING":    "Treadmill_Running",
    "INDOOR_CYCLING":       "Indoor_Cycling",
    "CROSS_COUNTRY_SKIING": "Cross_Country_Skiing",
    "BOXING":               "Boxing",
    "KICKBOXING":           "Kickboxing",
    "INDOOR_ROWING":        "Indoor_Rowing",
}

def parse_duration(duration_str):
    """Convertit PT1H30M45S en secondes"""
    if not duration_str:
        return 0.0
    s = duration_str.replace("PT", "")
    seconds = 0.0
    if "H" in s:
        h, s = s.split("H")
        seconds += float(h) * 3600
    if "M" in s:
        m, s = s.split("M")
        seconds += float(m) * 60
    if "S" in s:
        seconds += float(s.replace("S", ""))
    return seconds

def create_transaction():
    r = requests.post(f"{BASE_URL}/exercise-transactions", headers=HEADERS)
    if r.status_code == 204:
        print("ℹ️  Aucune nouvelle séance disponible")
        return None
    elif r.status_code == 201:
        tid = r.json().get("transaction-id")
        print(f"✅ Transaction créée : {tid}")
        return tid
    else:
        print(f"❌ Erreur : {r.status_code} {r.text}")
        return None

def get_exercises(transaction_id):
    r = requests.get(f"{BASE_URL}/exercise-transactions/{transaction_id}", headers=HEADERS)
    exercises = r.json().get("exercises", [])
    print(f"📋 {len(exercises)} séance(s) trouvée(s)")
    return exercises

def get_exercise_detail(exercise_url):
    r = requests.get(exercise_url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()
    print(f"⚠️  Erreur récupération : {r.status_code}")
    return {}

def save_to_file(exercise):
    """Sauvegarde JSON dans data/extracted/"""
    start_time  = exercise.get("start-time", "unknown")
    exercise_id = exercise.get("id", "unknown")
    filename = f"training-session-{start_time[:10]}T{start_time[11:19].replace(':', '')}-{exercise_id}-accesslink.json"
    filepath = DATA_DIR / filename
    with open(filepath, "w") as f:
        json.dump(exercise, f, indent=2)
    print(f"💾 Sauvegardé : {filename}")

def write_to_influx(exercise):
    """Ingère une séance dans InfluxDB"""
    start_time = exercise.get("start-time")
    if not start_time:
        print("⚠️  Pas de start-time, séance ignorée")
        return

    # Priorité detailed-sport-info sur sport (ex: OTHER -> BOXING)
    sport_raw = exercise.get("detailed-sport-info") or exercise.get("sport", "UNKNOWN")
    sport_raw = sport_raw.upper().replace("-", "_")
    sport     = SPORT_MAPPING.get(sport_raw, sport_raw.title())

    hr       = exercise.get("heart-rate") or {}
    hr_avg   = float(hr.get("average") or 0)
    hr_max   = float(hr.get("maximum") or 0)
    distance = float(exercise.get("distance") or 0)
    calories = float(exercise.get("calories") or 0)
    duration = parse_duration(exercise.get("duration", "PT0S"))
    device   = exercise.get("device-id", "UNKNOWN")

    client = InfluxDBClient(
        url=os.getenv("INFLUX_URL"),
        token=os.getenv("INFLUX_TOKEN"),
        org=os.getenv("INFLUX_ORG")
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)

    point = (
        Point("training_session")
        .tag("sport",    sport)
        .tag("deviceId", device)
        .field("duration_sec", duration)
        .field("calories",     calories)
        .field("distance",     distance)
        .field("hr_avg",       hr_avg)
        .field("hr_max",       hr_max)
        .time(start_time, WritePrecision.NS)
    )

    write_api.write(bucket=os.getenv("INFLUX_BUCKET"), record=point)
    print(f"📊 Ingéré : {start_time[:19]} | {sport} | {distance:.0f}m | {calories:.0f}kcal")

def commit_transaction(transaction_id):
    r = requests.put(f"{BASE_URL}/exercise-transactions/{transaction_id}", headers=HEADERS)
    if r.status_code == 200:
        print(f"✅ Transaction {transaction_id} commitée")
    else:
        print(f"⚠️  Commit : {r.status_code}")

if __name__ == "__main__":
    print("🚀 Récupération nouvelles séances Polar...\n")

    tid = create_transaction()
    if not tid:
        exit(0)

    exercise_urls = get_exercises(tid)

    count = 0
    for url in exercise_urls:
        ex = get_exercise_detail(url)
        if not ex:
            continue
        save_to_file(ex)
        write_to_influx(ex)
        count += 1

    commit_transaction(tid)
    print(f"\n✅ Terminé : {count} séance(s) ingérée(s)")
