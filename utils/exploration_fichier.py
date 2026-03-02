#!/usr/bin/env python3
import json
from pathlib import Path
from collections import Counter

DATA_DIR = Path.home() / "cde/polar/data/extracted"

sports_counter = Counter()
device_ids = set()
hr_missing = 0
distance_missing = 0
calories_missing = 0
duration_missing = 0
multi_object_files = []

files = list(DATA_DIR.glob("training-session-*.json"))
print(f"📂 {len(files)} fichiers trouvés")

for f in files:
    try:
        # lecture du fichier
        text = f.read_text()
        # vérifier si fichier multi-objets JSON (plusieurs {} concaténés)
        if text.strip().count("{") > 1 and text.strip().count("}") > 1:
            # essayer jsonlines ou signaler
            try:
                data_list = [json.loads(line) for line in text.strip().split("\n") if line.strip()]
                multi_object_files.append(str(f))
                # on prend juste le premier objet pour les stats globales
                data = data_list[0]
            except:
                multi_object_files.append(str(f))
                continue
        else:
            data = json.loads(text)

        # sport
        sport_raw = data.get("sport", {})
        if isinstance(sport_raw, dict):
            sport_id = sport_raw.get("id", "unknown")
        else:
            sport_id = str(sport_raw)
        sports_counter[sport_id] += 1

        # deviceId
        device_ids.add(data.get("deviceId", "UNKNOWN"))

        # HR
        if data.get("hrAvg") is None or data.get("hrMax") is None:
            hr_missing += 1

        # distance
        if data.get("distanceMeters") is None:
            distance_missing += 1

        # calories
        if data.get("calories") is None:
            calories_missing += 1

        # duration
        if data.get("durationMillis") is None:
            duration_missing += 1

    except json.JSONDecodeError:
        multi_object_files.append(str(f))
    except Exception as e:
        print(f"⚠️ Erreur fichier {f}: {e}")

# résultats
print("\n🏷️ Sports (ID et occurrences):")
for k, v in sports_counter.most_common():
    print(f"{k}: {v} occurrences")

print("\n🖥️ Device IDs uniques:")
print(device_ids)

print("\n❤️ Fichiers sans HR:", hr_missing)
print("📏 Fichiers sans distance:", distance_missing)
print("🔥 Fichiers sans calories:", calories_missing)
print("⏱️ Fichiers sans duration:", duration_missing)
print("\n📑 Fichiers multi-objets JSON détectés:", len(multi_object_files))
for f in multi_object_files[:10]:
    print(" -", f)
