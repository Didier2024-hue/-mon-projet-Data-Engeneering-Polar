from pathlib import Path
import json

input_file = Path.home() / "cde/polar/data/preprocessed/training-session.jsonl"
output_file = Path.home() / "cde/polar/data/preprocessed/training-session_clean.jsonl"

with input_file.open() as f_in, output_file.open("w") as f_out:
    for line in f_in:
        try:
            obj = json.loads(line)
            if "startTime" in obj and "deviceId" in obj:
                f_out.write(json.dumps(obj) + "\n")
        except:
            continue

print(f"✅ Fichier clean créé : {output_file}")
