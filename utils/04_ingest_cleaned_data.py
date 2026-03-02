#!/usr/bin/env python3
import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision

ENV_PATH = Path.home() / "cde/polar/.env"
load_dotenv(dotenv_path=ENV_PATH)

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "polar_metrics")

JSONL_FILE = Path.home() / "cde/polar/data/preprocessed/training-session_clean.jsonl"

SPORT_MAPPING = {
    "1":   "Running",
    "2":   "Cycling",
    "3":   "Walking",
    "4":   "Mountain_Biking",
    "5":   "Skiing",
    "11":  "Strength_Training",
    "15":  "Fitness_Dancing",
    "16":  "Aerobics",
    "17":  "Swimming",
    "18":  "Pool_Swimming",
    "23":  "Hiking",
    "38":  "Treadmill_Running",
    "62":  "Indoor_Cycling",
    "83":  "Cross_Country_Skiing",
    "103": "Pool_Swimming",
    "109": "Boxing",
    "110": "Kickboxing",
    "117": "Indoor_Rowing",
}

NAME_TO_SPORT = {
    "course à pied":      "Running",
    "jogging":            "Running",
    "running":            "Running",
    "nat. en piscine":    "Pool_Swimming",
    "natation en piscine": "Pool_Swimming",
    "vélo d'intérieur":   "Indoor_Cycling",
    "vélo de route":      "Cycling",
    "cyclisme":           "Cycling",
    "aviron en salle":    "Indoor_Rowing",
    "marche à pied":      "Walking",
    "kickboxing":         "Kickboxing",
    "séance musc.":       "Strength_Training",
    "boxe":               "Boxing",
    "autre sport int":    "Other_Indoor",
    "autre sport ex":     "Other_Outdoor",
    "other indoor":       "Other_Indoor",
}

def iso_to_datetime(ts):
    return datetime.fromisoformat(ts.replace("Z", ""))

def resolve_sport(data):
    sport_raw = data.get("sport")
    if sport_raw and isinstance(sport_raw, dict):
        sport_id = sport_raw.get("id", "")
        return SPORT_MAPPING.get(sport_id)
    # Fallback sur le nom
    name = data.get("name", "").lower().strip()
    return NAME_TO_SPORT.get(name)

def ingest_training_sessions():
    with InfluxDBClient(url=str(INFLUX_URL), token=str(INFLUX_TOKEN), org=str(INFLUX_ORG)) as client:
        write_api = client.write_api()

        count = 0
        skipped = 0

        with JSONL_FILE.open() as f:
            for line in f:
                try:
                    data = json.loads(line)

                    start_time = data.get("startTime")
                    device_id = data.get("deviceId")
                    if not start_time or not device_id:
                        skipped += 1
                        continue

                    sport = resolve_sport(data)
                    if not sport:
                        skipped += 1
                        continue

                    hr_avg = float(data.get("hrAvg") or 0)
                    hr_max = float(data.get("hrMax") or 0)
                    distance = float(data.get("distanceMeters") or 0)
                    calories = float(data.get("calories") or 0)
                    duration_sec = float(data.get("durationMillis") or 0) / 1000

                    point = (
                        Point("training_session")
                        .tag("sport", sport)
                        .tag("deviceId", device_id)
                        .field("distance", distance)
                        .field("calories", calories)
                        .field("duration_sec", duration_sec)
                        .field("hr_avg", hr_avg)
                        .field("hr_max", hr_max)
                        .time(iso_to_datetime(start_time), WritePrecision.NS)
                    )

                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
                    count += 1

                except Exception as e:
                    print(f"⚠️ Ligne ignorée : {e}")
                    skipped += 1

        print(f"✅ Ingestion terminée : {count} séances ingérées, {skipped} ignorées.")

if __name__ == "__main__":
    ingest_training_sessions()
