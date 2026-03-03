#!/usr/bin/env python3
"""
Chatbot Polar - Coach sportif IA
Interroge tes données Polar via Claude API
"""
import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / "cde/polar/.env")

sys.path.insert(0, str(Path.home() / "cde/polar/mcp"))
from polar_mcp_server import (
    get_recent_sessions,
    get_stats_by_sport,
    get_weekly_load,
    get_hr_zones,
    USER_INFO
)

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_MODEL   = "claude-opus-4-5"

if not CLAUDE_API_KEY:
    print("❌ CLAUDE_API_KEY manquante dans .env")
    sys.exit(1)

# ── Outils disponibles pour Claude ──────────────────────────────────────────
TOOLS = [
    {
        "name": "get_recent_sessions",
        "description": "Récupère les dernières séances d'entraînement de Didier avec distance, calories, durée et fréquence cardiaque",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Nombre de jours en arrière (défaut: 30)"}
            }
        }
    },
    {
        "name": "get_stats_by_sport",
        "description": "Statistiques moyennes par sport (distance, calories, durée, FC moyenne) sur une période donnée",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Nombre de jours en arrière (défaut: 90)"}
            }
        }
    },
    {
        "name": "get_weekly_load",
        "description": "Charge d'entraînement hebdomadaire - nombre de séances par semaine sur les dernières semaines",
        "input_schema": {
            "type": "object",
            "properties": {
                "weeks": {"type": "integer", "description": "Nombre de semaines (défaut: 8)"}
            }
        }
    },
    {
        "name": "get_hr_zones",
        "description": "Analyse des zones de fréquence cardiaque par sport - permet d'évaluer l'intensité des entraînements",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Nombre de jours (défaut: 30)"}
            }
        }
    },
    {
        "name": "get_user_profile",
        "description": "Profil de l'athlète : âge, poids, taille, FC max théorique, sports pratiqués",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

# ── Exécution des outils ─────────────────────────────────────────────────────
def execute_tool(name, arguments):
    print(f"  🔧 [{name}]", end=" ", flush=True)
    try:
        if name == "get_recent_sessions":
            result = get_recent_sessions(arguments.get("days", 30))
        elif name == "get_stats_by_sport":
            result = get_stats_by_sport(arguments.get("days", 90))
        elif name == "get_weekly_load":
            result = get_weekly_load(arguments.get("weeks", 8))
        elif name == "get_hr_zones":
            result = get_hr_zones(arguments.get("days", 30))
        elif name == "get_user_profile":
            result = USER_INFO
        else:
            result = {"error": f"Outil inconnu : {name}"}
        print("✓")
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"❌ {e}")
        return json.dumps({"error": str(e)})

# ── Appel API Claude avec boucle tool use ────────────────────────────────────
def ask_claude(messages):
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    system_prompt = f"""Tu es un coach sportif expert qui analyse les données d'entraînement de Didier.

Profil athlète :
- Âge : {USER_INFO['age']} ans, Poids : {USER_INFO['weight_kg']} kg, Taille : {USER_INFO['height_cm']} cm
- FC max : {USER_INFO['max_hr']} bpm
- Sports pratiqués : {', '.join(USER_INFO['sports'])}

Instructions :
- Réponds toujours en français
- Utilise les outils pour récupérer les données avant de répondre
- Donne des conseils personnalisés basés sur les données réelles
- Identifie les tendances, progrès et points d'amélioration
- Sois encourageant mais précis dans tes recommandations
- Propose des objectifs concrets et réalisables"""

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 2048,
        "system": system_prompt,
        "tools": TOOLS,
        "messages": messages
    }

    # Boucle tool use
    while True:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            return f"❌ Erreur API : {response.status_code} - {response.text}"

        data = response.json()
        stop_reason = data.get("stop_reason")
        content     = data.get("content", [])

        # Réponse finale
        if stop_reason == "end_turn":
            for block in content:
                if block.get("type") == "text":
                    return block["text"]
            return "Pas de réponse textuelle."

        # Tool use
        if stop_reason == "tool_use":
            # Ajouter la réponse de Claude aux messages
            payload["messages"].append({"role": "assistant", "content": content})

            # Exécuter tous les outils demandés
            tool_results = []
            for block in content:
                if block.get("type") == "tool_use":
                    tool_result = execute_tool(block["name"], block.get("input", {}))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": tool_result
                    })

            # Ajouter les résultats et continuer
            payload["messages"].append({"role": "user", "content": tool_results})
            continue

        return "Réponse inattendue de l'API."

# ── Interface chatbot ─────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("🏋️  COACH SPORTIF POLAR - Powered by Claude")
    print("=" * 60)
    print("Pose tes questions sur tes entraînements.")
    print("Tape 'quit' pour quitter.\n")

    messages = []

    while True:
        try:
            question = input("Tu : ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir ! 💪")
            break

        if not question:
            continue
        if question.lower() in ["quit", "exit", "q"]:
            print("Au revoir ! 💪")
            break

        messages.append({"role": "user", "content": question})

        print("Coach : ", end="", flush=True)
        response = ask_claude(messages)
        print(f"\n{response}\n")

        messages.append({"role": "assistant", "content": response})

        # Garder l'historique limité à 10 échanges
        if len(messages) > 20:
            messages = messages[-20:]

if __name__ == "__main__":
    main()
