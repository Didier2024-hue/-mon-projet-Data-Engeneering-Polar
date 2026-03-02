import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision

load_dotenv()

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

DATA_DIR = Path.home() / "cde/polar/data/extracted"

def iso_to_datetime(ts):
    return datetime.fromisoformat(ts.replace("Z", ""))

def parse_duration(duration_str):
    return float(duration_str.replace("PT", "").replace("S", ""))

def ingest_training_sessions():
    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        write_api = client.write_api()

        files = list(DATA_DIR.rglob("training-session-*.json"))
        print(f"{len(files)} training files found")

        for file in files:
            with open(file) as f:
                data = json.load(f)

            if not data.get("exercises"):
                continue

            exercise = data["exercises"][0]

            point = (
                Point("training_session")
                .tag("sport", exercise.get("sport", "UNKNOWN"))
                .tag("deviceId", data.get("deviceId", "UNKNOWN"))
                .field("distance", float(exercise.get("distance", 0)))
                .field("calories", float(exercise.get("kiloCalories", 0)))
                .field("duration_sec", parse_duration(exercise.get("duration", "PT0S")))
                .field("avg_speed", float(exercise.get("speed", {}).get("avg", 0)))
                .field("max_speed", float(exercise.get("speed", {}).get("max", 0)))
                .field("avg_cadence", float(exercise.get("cadence", {}).get("avg", 0)))
                .field("max_cadence", float(exercise.get("cadence", {}).get("max", 0)))
                .time(iso_to_datetime(exercise["startTime"]), WritePrecision.NS)
            )

            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

    print("Ingestion complete.")

if __name__ == "__main__":
    ingest_training_sessions()