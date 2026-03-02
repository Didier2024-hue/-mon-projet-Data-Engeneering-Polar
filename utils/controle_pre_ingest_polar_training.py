#!/usr/bin/env python3
import json
from pathlib import Path

PREPROCESSED_FILE = Path.home() / "cde/polar/data/preprocessed/training-session.jsonl"

valid_count = 0
invalid_count = 0
with PREPROCESSED_FILE.open() as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            # Contrôle minimum : startTime et deviceId doivent exister
            if "startTime" in obj and "deviceId" in obj:
                valid_count += 1
            else:
                invalid_count += 1
                print(f"⚠️ Ligne {i} invalide : manque startTime ou deviceId")
        except Exception as e:
            invalid_count += 1
            print(f"⚠️ Ligne {i} invalide : {e}")

print(f"✅ Lignes valides : {valid_count}")
print(f"❌ Lignes invalides : {invalid_count}")
