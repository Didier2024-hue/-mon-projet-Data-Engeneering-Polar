#!/usr/bin/env python3
from influxdb_client import InfluxDBClient
from pathlib import Path
from dotenv import load_dotenv
import os

# --- Charger .env explicitement ---
ENV_PATH = Path.home() / "cde/polar/.env"
if not ENV_PATH.exists():
    raise FileNotFoundError(f".env introuvable : {ENV_PATH}")
load_dotenv(dotenv_path=ENV_PATH)

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")

# Vérification simple
if not all([INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG]):
    raise ValueError(f"Une variable d'environnement est manquante : "
                     f"INFLUX_URL={INFLUX_URL}, INFLUX_TOKEN={INFLUX_TOKEN}, INFLUX_ORG={INFLUX_ORG}")

print(f"✅ Variables chargées correctement :\nURL={INFLUX_URL}\nORG={INFLUX_ORG}")

# --- Connexion et purge du bucket ---
with InfluxDBClient(url=str(INFLUX_URL), token=str(INFLUX_TOKEN), org=str(INFLUX_ORG)) as client:
    buckets_api = client.buckets_api()
    
    bucket_name = "polar_metrics"
    
    # Supprimer si existe
    bucket = buckets_api.find_bucket_by_name(bucket_name)
    if bucket:
        buckets_api.delete_bucket(bucket)
        print(f"✅ Bucket '{bucket_name}' supprimé")
    else:
        print(f"ℹ️ Bucket '{bucket_name}' n'existait pas")
    
    # Créer bucket vide
    buckets_api.create_bucket(bucket_name=bucket_name, org=INFLUX_ORG, retention_rules=[])
    print(f"✅ Bucket '{bucket_name}' créé et vide")