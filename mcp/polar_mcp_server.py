#!/usr/bin/env python3
"""
MCP Server Polar - Coach sportif IA
Permet à Claude d'interroger les données Polar et de faire des recommandations
"""
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from influxdb_client import InfluxDBClient

load_dotenv(Path.home() / "cde/polar/.env")

INFLUX_URL    = os.getenv("INFLUX_URL")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN")
INFLUX_ORG    = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "polar_metrics")

USER_INFO = {
    "name": "Didier",
    "age": 56,
    "weight_kg": 89,
    "height_cm": 170,
    "max_hr": 185,
    "sports": ["Pool_Swimming", "Running", "Hiking", "Indoor_Rowing"]
}

# ── Connexion InfluxDB ───────────────────────────────────────────────────────
def get_client():
    return InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

def query_influx(flux_query):
    with get_client() as client:
        tables = client.query_api().query(flux_query)
        records = []
        for table in tables:
            for record in table.records:
                records.append({
                    "time": str(record.values.get("_time", "")),
                    "sport": record.values.get("sport", ""),
                    "field": record.values.get("_field", ""),
                    "value": record.get_value()
                })
        return records

# ── Requêtes Flux ────────────────────────────────────────────────────────────

def get_recent_sessions(days=30):
    q = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{days}d)
      |> filter(fn: (r) => r._measurement == "training_session")
      |> filter(fn: (r) => r._field == "distance" or r._field == "calories"
          or r._field == "duration_sec" or r._field == "hr_avg" or r._field == "hr_max")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: 20)
    '''
    with get_client() as client:
        tables = client.query_api().query(q)
        sessions = []
        for table in tables:
            for r in table.records:
                sessions.append({
                    "date": str(r.get_time())[:19],
                    "sport": r.values.get("sport", ""),
                    "distance_m": r.values.get("distance", 0),
                    "calories": r.values.get("calories", 0),
                    "duration_min": round((r.values.get("duration_sec", 0) or 0) / 60, 1),
                    "hr_avg": r.values.get("hr_avg", 0),
                    "hr_max": r.values.get("hr_max", 0),
                })
        return sessions

def get_stats_by_sport(days=90):
    q = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{days}d)
      |> filter(fn: (r) => r._measurement == "training_session")
      |> filter(fn: (r) => r._field == "distance" or r._field == "calories"
          or r._field == "duration_sec" or r._field == "hr_avg")
      |> group(columns: ["sport", "_field"])
      |> mean()
    '''
    records = query_influx(q)
    stats = {}
    for r in records:
        sport = r["sport"]
        if sport not in stats:
            stats[sport] = {}
        stats[sport][r["field"]] = round(r["value"] or 0, 1)
    return stats

def get_weekly_load(weeks=8):
    q = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{weeks * 7}d)
      |> filter(fn: (r) => r._measurement == "training_session")
      |> filter(fn: (r) => r._field == "duration_sec")
      |> group()
      |> aggregateWindow(every: 1w, fn: count, createEmpty: true)
    '''
    records = query_influx(q)
    return [{"week": r["time"][:10], "sessions": int(r["value"] or 0)} for r in records]

def get_hr_zones(days=30):
    """Analyse des zones FC sur les dernières séances"""
    q = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{days}d)
      |> filter(fn: (r) => r._measurement == "training_session")
      |> filter(fn: (r) => r._field == "hr_avg")
      |> filter(fn: (r) => r._value > 50)
      |> group(columns: ["sport"])
      |> mean()
    '''
    records = query_influx(q)
    max_hr = USER_INFO["max_hr"]
    zones = []
    for r in records:
        hr = r["value"] or 0
        pct = round(hr / max_hr * 100, 1)
        if pct < 60:
            zone = "Zone 1 - Récupération"
        elif pct < 70:
            zone = "Zone 2 - Endurance"
        elif pct < 80:
            zone = "Zone 3 - Aérobie"
        elif pct < 90:
            zone = "Zone 4 - Seuil"
        else:
            zone = "Zone 5 - Maximum"
        zones.append({
            "sport": r["sport"],
            "hr_avg": round(hr, 1),
            "pct_max": pct,
            "zone": zone
        })
    return zones

# ── MCP Server ───────────────────────────────────────────────────────────────
server = Server("polar-coach")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_recent_sessions",
            description="Récupère les dernières séances d'entraînement de Didier (distance, calories, durée, FC)",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Nombre de jours en arrière (défaut: 30)", "default": 30}
                }
            }
        ),
        Tool(
            name="get_stats_by_sport",
            description="Statistiques moyennes par sport (distance, calories, durée, FC) sur une période",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Nombre de jours en arrière (défaut: 90)", "default": 90}
                }
            }
        ),
        Tool(
            name="get_weekly_load",
            description="Charge d'entraînement hebdomadaire - nombre de séances par semaine",
            inputSchema={
                "type": "object",
                "properties": {
                    "weeks": {"type": "integer", "description": "Nombre de semaines (défaut: 8)", "default": 8}
                }
            }
        ),
        Tool(
            name="get_hr_zones",
            description="Analyse des zones de fréquence cardiaque par sport - intensité des entraînements",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Nombre de jours (défaut: 30)", "default": 30}
                }
            }
        ),
        Tool(
            name="get_user_profile",
            description="Profil de l'athlète : âge, poids, taille, FC max, sports pratiqués",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]

@server.call_tool()
async def call_tool(name, arguments):
    try:
        if name == "get_recent_sessions":
            days = arguments.get("days", 30)
            data = get_recent_sessions(days)
            result = f"📋 {len(data)} séances sur les {days} derniers jours :\n\n"
            for s in data:
                result += (
                    f"• {s['date'][:10]} | {s['sport']} | "
                    f"{s['duration_min']}min | "
                    f"{s['distance_m']:.0f}m | "
                    f"{s['calories']:.0f}kcal | "
                    f"FC moy: {s['hr_avg']:.0f} max: {s['hr_max']:.0f}\n"
                )

        elif name == "get_stats_by_sport":
            days = arguments.get("days", 90)
            data = get_stats_by_sport(days)
            result = f"📊 Statistiques moyennes par sport ({days} jours) :\n\n"
            for sport, stats in data.items():
                result += f"🏅 {sport} :\n"
                if "distance" in stats:
                    result += f"   Distance moy : {stats['distance']:.0f} m\n"
                if "calories" in stats:
                    result += f"   Calories moy : {stats['calories']:.0f} kcal\n"
                if "duration_sec" in stats:
                    result += f"   Durée moy    : {stats['duration_sec']/60:.0f} min\n"
                if "hr_avg" in stats:
                    result += f"   FC moy       : {stats['hr_avg']:.0f} bpm\n"
                result += "\n"

        elif name == "get_weekly_load":
            weeks = arguments.get("weeks", 8)
            data = get_weekly_load(weeks)
            result = f"📅 Charge hebdomadaire ({weeks} semaines) :\n\n"
            for w in data:
                bars = "█" * int(w["sessions"])
                result += f"• {w['week']} : {bars} {w['sessions']} séances\n"

        elif name == "get_hr_zones":
            days = arguments.get("days", 30)
            data = get_hr_zones(days)
            result = f"❤️ Zones FC ({days} jours) :\n\n"
            for z in data:
                result += (
                    f"• {z['sport']} : {z['hr_avg']} bpm "
                    f"({z['pct_max']}% FCmax) → {z['zone']}\n"
                )

        elif name == "get_user_profile":
            result = f"""👤 Profil athlète :
• Nom       : {USER_INFO['name']}
• Âge       : {USER_INFO['age']} ans
• Poids     : {USER_INFO['weight_kg']} kg
• Taille    : {USER_INFO['height_cm']} cm
• FC max    : {USER_INFO['max_hr']} bpm
• Sports    : {', '.join(USER_INFO['sports'])}
"""
        else:
            result = f"Outil inconnu : {name}"

        return [TextContent(type="text", text=result)]

    except Exception as e:
        return [TextContent(type="text", text=f"❌ Erreur : {str(e)}")]

# ── Main ─────────────────────────────────────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
