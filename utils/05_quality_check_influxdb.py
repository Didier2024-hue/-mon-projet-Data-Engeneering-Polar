#!/usr/bin/env python3
import os
from influxdb_client import InfluxDBClient
from influxdb_client.client.flux_table import FluxStructureEncoder
from dotenv import load_dotenv
import pandas as pd

# --- Charger .env ---
load_dotenv(os.path.expanduser("~/cde/polar/.env"))

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "polar_metrics")

def fetch_data():
    query = f'''
    from(bucket:"{INFLUX_BUCKET}")
      |> range(start: -20y)
      |> filter(fn: (r) => r._measurement == "training_session")
    '''
    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        query_api = client.query_api()
        tables = query_api.query(query)
        records = []
        for table in tables:
            for record in table.records:
                rec = {
                    "time": record.get_time(),
                    "sport": record.values.get("sport"),
                    "deviceId": record.values.get("deviceId"),
                    "field": record.get_field(),
                    "value": record.get_value()
                }
                records.append(rec)
    return pd.DataFrame(records)

def pivot_fields(df):
    # Transformer les champs en colonnes
    df_pivot = df.pivot_table(index=["time","sport","deviceId"], 
                              columns="field", 
                              values="value",
                              aggfunc="first").reset_index()
    return df_pivot

def compute_stats(df):
    stats = {}
    stats["total_sessions"] = len(df)
    stats["sessions_per_sport"] = df["sport"].value_counts().to_dict()
    
    metrics = ["distance", "calories", "duration_sec", "hr_avg", "hr_max"]
    for m in metrics:
        stats[m] = {
            "mean": df[m].mean(),
            "min": df[m].min(),
            "max": df[m].max(),
            "missing": df[m].isna().sum()
        }
    return stats

if __name__ == "__main__":
    print("📊 Extraction des données depuis InfluxDB...")
    df_raw = fetch_data()
    print(f"📂 {len(df_raw)} lignes extraites (brutes)")

    df = pivot_fields(df_raw)
    print(f"📂 {len(df)} séances uniques après pivot")

    stats = compute_stats(df)

    print("\n=== Résumé global ===")
    print(f"Total séances : {stats['total_sessions']}")
    print("Séances par sport :")
    for k,v in stats["sessions_per_sport"].items():
        print(f"  - {k} : {v}")
    print("\n📏 Statistiques par métrique :")
    for metric, mstats in stats.items():
        if metric == "total_sessions" or metric == "sessions_per_sport":
            continue
        print(f"\n{metric} :")
        print(f"  - Moyenne : {mstats['mean']:.2f}")
        print(f"  - Min : {mstats['min']:.2f}")
        print(f"  - Max : {mstats['max']:.2f}")
        print(f"  - Valeurs manquantes : {mstats['missing']}")
