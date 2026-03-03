#!/usr/bin/env python3
"""Flask Backend - Coach Sportif Polar"""
import os, sys, json
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import plotly.graph_objects as go
import plotly.utils
import anthropic

load_dotenv(Path.home() / "cde/polar/.env")
sys.path.insert(0, str(Path.home() / "cde/polar/mcp"))

from polar_mcp_server import (
    get_recent_sessions, get_stats_by_sport,
    get_weekly_load, get_hr_zones, USER_INFO
)

app = Flask(__name__)
CORS(app)

CLAUDE_MODEL = "claude-sonnet-4-20250514"
client_ai = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

TOOLS = [
    {"name": "get_recent_sessions",
     "description": "Récupère les dernières séances d'entraînement de Didier",
     "input_schema": {"type": "object", "properties": {
         "days": {"type": "integer", "description": "Nombre de jours (défaut: 30)"}}}},
    {"name": "get_stats_by_sport",
     "description": "Statistiques moyennes par sport",
     "input_schema": {"type": "object", "properties": {
         "days": {"type": "integer", "description": "Nombre de jours (défaut: 90)"}}}},
    {"name": "get_weekly_load",
     "description": "Charge hebdomadaire - séances par semaine",
     "input_schema": {"type": "object", "properties": {
         "weeks": {"type": "integer", "description": "Nombre de semaines (défaut: 8)"}}}},
    {"name": "get_hr_zones",
     "description": "Zones de fréquence cardiaque par sport",
     "input_schema": {"type": "object", "properties": {
         "days": {"type": "integer", "description": "Nombre de jours (défaut: 30)"}}}},
    {"name": "get_user_profile",
     "description": "Profil de l'athlète",
     "input_schema": {"type": "object", "properties": {}}}
]

SYSTEM_PROMPT = f"""Tu es POLAR COACH, un coach sportif expert et bienveillant qui analyse les données d'entraînement de Didier.
Profil : Age {USER_INFO['age']} ans | {USER_INFO['weight_kg']}kg | {USER_INFO['height_cm']}cm | FC max {USER_INFO['max_hr']} bpm
Sports : {', '.join(USER_INFO['sports'])}
- Réponds TOUJOURS en français
- Utilise les outils pour récupérer les données réelles
- Donne des conseils personnalisés, précis et encourageants
- Identifie tendances, progrès et points d'amélioration
- Propose des objectifs concrets et réalisables"""

def execute_tool(name, arguments):
    try:
        if name == "get_recent_sessions": return get_recent_sessions(arguments.get("days", 30))
        elif name == "get_stats_by_sport": return get_stats_by_sport(arguments.get("days", 90))
        elif name == "get_weekly_load": return get_weekly_load(arguments.get("weeks", 8))
        elif name == "get_hr_zones": return get_hr_zones(arguments.get("days", 30))
        elif name == "get_user_profile": return USER_INFO
        return {"error": f"Outil inconnu: {name}"}
    except Exception as e:
        return {"error": str(e)}

def ask_claude(messages):
    msgs = messages.copy()
    while True:
        response = client_ai.messages.create(
            model=CLAUDE_MODEL, max_tokens=2048,
            system=SYSTEM_PROMPT, tools=TOOLS, messages=msgs
        )
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"): return block.text
            return "Pas de réponse."
        if response.stop_reason == "tool_use":
            msgs.append({"role": "assistant", "content": [b.model_dump() for b in response.content]})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str)
                    })
            msgs.append({"role": "user", "content": tool_results})
        else:
            return "Erreur inattendue."

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    try:
        response = ask_claude(data.get("messages", []))
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats")
def stats():
    sessions = get_recent_sessions(30)
    return jsonify({
        "sessions": len(sessions),
        "calories": round(sum(s["calories"] for s in sessions)),
        "hours": round(sum(s["duration_min"] for s in sessions) / 60, 1),
        "km": round(sum(s["distance_m"] for s in sessions) / 1000, 1)
    })

def chart_layout():
    return dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0", family="Space Mono"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        margin=dict(l=20, r=20, t=10, b=40), height=200
    )

@app.route("/api/charts/weekly")
def chart_weekly():
    data = get_weekly_load(8)
    weeks = [d["week"] for d in data]
    sessions = [d["sessions"] for d in data]
    colors = ["#00d4ff" if s >= 4 else "#ff6b35" if s <= 2 else "#7fff7f" for s in sessions]
    fig = go.Figure(go.Bar(x=weeks, y=sessions, marker_color=colors, text=sessions, textposition="outside"))
    fig.update_layout(**chart_layout())
    return jsonify(json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig)))

@app.route("/api/charts/sports")
def chart_sports():
    data = get_stats_by_sport(90)
    sports = list(data.keys())
    calories = [data[s].get("calories", 0) for s in sports]
    fig = go.Figure(go.Bar(
        x=sports, y=calories,
        marker=dict(color=calories, colorscale=[[0,"#1a1a2e"],[0.5,"#ff6b35"],[1,"#00d4ff"]], showscale=False),
        text=[f"{c:.0f}" for c in calories], textposition="outside"
    ))
    l = chart_layout()
    l["yaxis"]["title"] = "Cal. moy."
    fig.update_layout(**l)
    return jsonify(json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig)))

@app.route("/api/charts/hr_zones")
def chart_hr_zones():
    data = get_hr_zones(30)
    sports = [d["sport"] for d in data]
    pcts = [d["pct_max"] for d in data]
    colors = ["#7fff7f" if p < 60 else "#00d4ff" if p < 70 else "#ffd700" if p < 80 else "#ff6b35" if p < 90 else "#ff4444" for p in pcts]
    fig = go.Figure(go.Bar(x=sports, y=pcts, marker_color=colors, text=[f"{p}%" for p in pcts], textposition="outside"))
    fig.add_hline(y=70, line_dash="dot", line_color="rgba(255,255,255,0.3)")
    fig.add_hline(y=80, line_dash="dot", line_color="rgba(255,165,0,0.4)")
    l = chart_layout()
    l["yaxis"]["range"] = [0, 100]
    l["yaxis"]["title"] = "% FC max"
    fig.update_layout(**l)
    return jsonify(json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig)))

@app.route("/")
def index():
    return render_template_string(open(Path(__file__).parent / "templates" / "index.html").read())

if __name__ == "__main__":
    print("Polar Coach sur http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5001, debug=False)
