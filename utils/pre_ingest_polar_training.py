#!/usr/bin/env python3
import json
from pathlib import Path

RAW_DIR = Path.home() / "cde/polar/data/extracted"
PREPROCESSED_DIR = Path.home() / "cde/polar/data/preprocessed"
PREPROCESSED_DIR.mkdir(exist_ok=True)

output_file = PREPROCESSED_DIR / "training-session.jsonl"

with output_file.open("w") as out_f:
    for f in RAW_DIR.glob("training-session-*.json"):
        try:
            text = f.read_text().strip()
            # Séparer les objets JSON multiples
            objects = []
            if text.startswith("[") and text.endswith("]"):
                # Cas tableau JSON
                objects = json.loads(text)
            else:
                # Cas multi-objets concaténés
                parts = text.replace("}\n{", "}|{").split("|")
                for part in parts:
                    obj_text = part.strip()
                    if not obj_text.startswith("{"):
                        obj_text = "{" + obj_text
                    if not obj_text.endswith("}"):
                        obj_text = obj_text + "}"
                    objects.append(json.loads(obj_text))

            # Écrire chaque objet dans le JSONL
            for obj in objects:
                out_f.write(json.dumps(obj))
                out_f.write("\n")

        except Exception as e:
            print(f"⚠️ Fichier {f} non traité: {e}")

print(f"✅ Prétraitement terminé. Fichier JSONL prêt: {output_file}")
