#!/usr/bin/env python3
import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision

# --- Charger .env ---
ENV_PATH = Path.home() / "cde/polar/.env"
load_dotenv(dotenv_path=ENV_PATH)

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "polar_metrics")

JSONL_FILE = Path.home() / "cde/polar/data/preprocessed/training-session_clean.jsonl"

SPORT_MAPPING = {
    "1": "Running",
    "2": "Cycling",
    "3": "Walking",
    "4": "Other",
    "5": "Strength",
    "11": "Skiing",
    "15": "Yoga",
    "16": "Pilates",
    "17": "Swimming",
    "18": "Pool Swimming",
    "23": "Hiking",
    "38": "Rowing",
    "62": "Treadmill",
    "83": "Elliptical",
    "103": "Indoor Cycling",
    "109": "Strength Training",
    "110": "Crossfit",
    "117": "Trail Running",
    "unknown": "Unknown"
}

def iso_to_datetime(ts):
    return datetime.fromisoformat(ts.replace("Z", ""))

def ingest_training_sessions():
    with InfluxDBClient(url=str(INFLUX_URL), token=str(INFLUX_TOKEN), org=str(INFLUX_ORG)) as client:
        write_api = client.write_api()

        count = 0
        with JSONL_FILE.open() as f:
            for line in f:
                try:
                    data = json.loads(line)
                    
                    start_time = data.get("startTime")
                    device_id = data.get("deviceId")
                    if not start_time or not device_id:
                        continue  # skip invalid

                    # --- sport mapping ---
                    sport_raw = data.get("sport", {"id": "unknown"})
                    if isinstance(sport_raw, dict):
                        sport = SPORT_MAPPING.get(sport_raw.get("id", "unknown"), "Unknown")
                    else:
                        sport = SPORT_MAPPING.get(str(sport_raw), "Unknown")

                    # --- heart rate ---
                    hr_avg = data.get("hrAvg", 0)
                    hr_max = data.get("hrMax", 0)

                    # --- metrics ---
                    distance = data.get("distanceMeters", 0)
                    calories = data.get("calories", 0)
                    duration_sec = data.get("durationMillis", 0) / 1000

                    # --- point InfluxDB ---
                    point = (
                        Point("training_session")
                        .tag("sport", sport)
                        .tag("deviceId", device_id)
                        .field("distance", float(distance))
                        .field("calories", float(calories))
                        .field("duration_sec", float(duration_sec))
                        .field("hr_avg", float(hr_avg))
                        .field("hr_max", float(hr_max))
                        .time(iso_to_datetime(start_time), WritePrecision.NS)
                    )

                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
                    count += 1
                except Exception as e:
                    print(f"⚠️ Ligne ignorée : {e}")

        print(f"✅ Ingestion terminée. {count} séances ingérées.")

if __name__ == "__main__":
    ingest_training_sessions()
