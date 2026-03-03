#!/usr/bin/env python3
"""
Test des fonctions du MCP Server Polar
"""
import sys
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

print("=== PROFIL ===")
print(USER_INFO)

print("\n=== SESSIONS RECENTES (30j) ===")
sessions = get_recent_sessions(30)
for s in sessions[:5]:
    print(s)

print("\n=== STATS PAR SPORT (90j) ===")
stats = get_stats_by_sport(90)
for sport, s in stats.items():
    print(f"{sport}: {s}")

print("\n=== CHARGE HEBDO (4 semaines) ===")
load = get_weekly_load(4)
for w in load:
    print(w)

print("\n=== ZONES FC (30j) ===")
zones = get_hr_zones(30)
for z in zones:
    print(z)

print("\nTout OK !")
