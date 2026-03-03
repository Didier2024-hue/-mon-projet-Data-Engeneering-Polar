#!/usr/bin/env python3
"""
Dashboard Grafana - Polar Performance v5
Fix : filtre sport correctement echappé, requetes validées
"""
import os
import requests
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

GRAFANA_URL     = os.getenv("GRAFANA_URL")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY")
B               = os.getenv("INFLUX_BUCKET", "polar_metrics")

if not GRAFANA_URL or not GRAFANA_API_KEY:
    raise ValueError("GRAFANA_URL ou GRAFANA_API_KEY non definie dans .env")

INFLUXDB_UID  = "bfesh7l4serr4e"
INFLUXDB_TYPE = "influxdb"
DS = {"type": INFLUXDB_TYPE, "uid": INFLUXDB_UID}

# Filtre sport — syntaxe Grafana correcte, pas d'accolades Python
SF = r'|> filter(fn: (r) => r.sport =~ /${sport:regex}/)'

print("Configuration chargee")

_panel_id = 1
def next_id():
    global _panel_id
    pid = _panel_id
    _panel_id += 1
    return pid

def base(field):
    return (
        'from(bucket: "' + B + '")\n'
        '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
        '  |> filter(fn: (r) => r._measurement == "training_session")\n'
        '  |> filter(fn: (r) => r._field == "' + field + '")\n'
        '  ' + SF + '\n'
    )

def q_count():
    return base("distance") + '  |> group()\n  |> count()'

def q_sum_km():
    return base("distance") + '  |> group()\n  |> sum()\n  |> map(fn: (r) => ({r with _value: r._value / 1000.0}))'

def q_sum_cal():
    return base("calories") + '  |> group()\n  |> sum()'

def q_sum_hours():
    return base("duration_sec") + '  |> group()\n  |> sum()\n  |> map(fn: (r) => ({r with _value: r._value / 3600.0}))'

def q_mean_hr():
    return (
        base("hr_avg") +
        '  |> filter(fn: (r) => r._value > 50)\n'
        '  |> group()\n  |> mean()'
    )

def q_max_hr():
    return (
        'from(bucket: "' + B + '")\n'
        '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
        '  |> filter(fn: (r) => r._measurement == "training_session")\n'
        '  |> filter(fn: (r) => r._field == "hr_max")\n'
        '  |> filter(fn: (r) => r._value < 220)\n'
        '  |> group()\n  |> max()'
    )

def q_timeseries(field, min_val=None):
    q = base(field)
    if min_val:
        q += '  |> filter(fn: (r) => r._value > ' + str(min_val) + ')\n'
    q += '  |> group(columns: ["sport"])\n'
    q += '  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)'
    return q

def q_pie():
    return (
        'from(bucket: "' + B + '")\n'
        '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
        '  |> filter(fn: (r) => r._measurement == "training_session")\n'
        '  |> filter(fn: (r) => r._field == "distance")\n'
        '  ' + SF + '\n'
        '  |> group(columns: ["sport"])\n'
        '  |> count()\n'
        '  |> set(key: "_field", value: "count")'
    )

def q_table():
    return (
        'from(bucket: "' + B + '")\n'
        '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
        '  |> filter(fn: (r) => r._measurement == "training_session")\n'
        '  |> filter(fn: (r) => r._field == "distance" or r._field == "calories"\n'
        '      or r._field == "duration_sec" or r._field == "hr_avg" or r._field == "hr_max")\n'
        '  ' + SF + '\n'
        '  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")\n'
        '  |> drop(columns: ["_start", "_stop", "_measurement", "deviceId"])\n'
        '  |> sort(columns: ["_time"], desc: true)\n'
        '  |> limit(n: 50)'
    )

# ── Constructeurs panels ─────────────────────────────────────────────────────

def stat_panel(title, query, unit, color, x, y, w=4, h=4):
    return {
        "type": "stat",
        "id": next_id(),
        "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": DS,
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "decimals": 1,
                "color": {"mode": "fixed", "fixedColor": color},
                "noValue": "0",
            },
            "overrides": []
        },
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "value",
            "colorMode": "background",
            "graphMode": "none",
            "justifyMode": "center",
        },
        "targets": [{"query": query, "refId": "A", "datasource": DS}]
    }

def timeseries_panel(title, query, unit, x, y, w=12, h=9):
    return {
        "type": "timeseries",
        "id": next_id(),
        "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": DS,
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "color": {"mode": "palette-classic"},
                "custom": {
                    "lineInterpolation": "smooth",
                    "showPoints": "never",
                    "spanNulls": True,
                    "fillOpacity": 15,
                    "gradientMode": "opacity",
                    "lineWidth": 2,
                }
            },
            "overrides": []
        },
        "options": {
            "legend": {
                "displayMode": "table",
                "placement": "bottom",
                "showLegend": True,
                "calcs": ["mean", "max", "sum"]
            },
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        "targets": [{"query": query, "refId": "A", "datasource": DS}]
    }

def piechart_panel(title, query, x, y, w=8, h=9):
    return {
        "type": "barchart",
        "id": next_id(),
        "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": DS,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "lineWidth": 1,
                    "fillOpacity": 80,
                }
            },
            "overrides": []
        },
        "options": {
            "barWidth": 0.7,
            "groupWidth": 0.7,
            "orientation": "horizontal",
            "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
            "tooltip": {"mode": "single"},
            "xTickLabelRotation": 0,
            "xField": "sport",
        },
        "transformations": [
            {"id": "labelsToFields", "options": {"valueLabel": "sport", "mode": "rows"}},
            {"id": "merge", "options": {}}
        ],
        "targets": [{"query": query, "refId": "A", "datasource": DS}]
    }

def table_panel(title, query, x, y, w=24, h=10):
    return {
        "type": "table",
        "id": next_id(),
        "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": DS,
        "options": {
            "showHeader": True,
            "sortBy": [{"displayName": "Date", "desc": True}],
            "footer": {"show": False},
        },
        "fieldConfig": {
            "defaults": {
                "custom": {"align": "center", "displayMode": "auto", "filterable": True}
            },
            "overrides": [
                {"matcher": {"id": "byName", "options": "_time"},
                 "properties": [{"id": "displayName", "value": "Date"},
                                {"id": "unit", "value": "dateTimeAsLocal"},
                                {"id": "custom.width", "value": 150}]},
                {"matcher": {"id": "byName", "options": "sport"},
                 "properties": [{"id": "displayName", "value": "Sport"},
                                {"id": "custom.width", "value": 130}]},
                {"matcher": {"id": "byName", "options": "distance"},
                 "properties": [{"id": "displayName", "value": "Distance"},
                                {"id": "unit", "value": "lengthm"},
                                {"id": "custom.width", "value": 120}]},
                {"matcher": {"id": "byName", "options": "duration_sec"},
                 "properties": [{"id": "displayName", "value": "Duree"},
                                {"id": "unit", "value": "s"},
                                {"id": "custom.width", "value": 100}]},
                {"matcher": {"id": "byName", "options": "calories"},
                 "properties": [{"id": "displayName", "value": "Calories"},
                                {"id": "unit", "value": "none"},
                                {"id": "custom.width", "value": 100}]},
                {"matcher": {"id": "byName", "options": "hr_avg"},
                 "properties": [
                     {"id": "displayName", "value": "FC Moy"},
                     {"id": "unit", "value": "none"},
                     {"id": "custom.width", "value": 110},
                     {"id": "custom.displayMode", "value": "color-background"},
                     {"id": "color", "value": {"mode": "thresholds"}},
                     {"id": "thresholds", "value": {
                         "mode": "absolute",
                         "steps": [
                             {"color": "green", "value": None},
                             {"color": "orange", "value": 130},
                             {"color": "red", "value": 160}
                         ]
                     }}
                 ]},
                {"matcher": {"id": "byName", "options": "hr_max"},
                 "properties": [{"id": "displayName", "value": "FC Max"},
                                {"id": "unit", "value": "none"},
                                {"id": "custom.width", "value": 110}]},
            ]
        },
        "targets": [{"query": query, "refId": "A", "datasource": DS, "format": "table"}]
    }

# ── Construction panels ──────────────────────────────────────────────────────
panels = []

# LIGNE 1 - KPIs
panels.append(stat_panel("Total Seances",    q_count(),     "none", "blue",     x=0,  y=0))
panels.append(stat_panel("Distance (km)",    q_sum_km(),    "km",   "green",    x=4,  y=0))
panels.append(stat_panel("Calories",         q_sum_cal(),   "kcal", "orange",   x=8,  y=0))
panels.append(stat_panel("Temps (h)",        q_sum_hours(), "h",    "purple",   x=12, y=0))
panels.append(stat_panel("FC Moyenne (bpm)", q_mean_hr(),   "none", "red",      x=16, y=0))
panels.append(stat_panel("FC Max (bpm)",     q_max_hr(),    "none", "dark-red", x=20, y=0))

# LIGNE 2 - Graphiques
panels.append(timeseries_panel("Distance par sport (m)", q_timeseries("distance"),    "lengthm", x=0,  y=4, w=12, h=9))
panels.append(timeseries_panel("FC Moyenne par sport",   q_timeseries("hr_avg", 50),  "none",    x=12, y=4, w=12, h=9))

# LIGNE 3 - Pie + Calories
# Panel Repartition supprime
panels.append(timeseries_panel("Calories par sport",  q_timeseries("calories"),       "kcal", x=0, y=13, w=24, h=9))

# LIGNE 4 - Tableau
panels.append(table_panel("Historique des Seances (50 dernieres)", q_table(),         x=0, y=22, w=24, h=10))

print(f"{len(panels)} panels construits")

# ── Dashboard ────────────────────────────────────────────────────────────────
dashboard = {
    "dashboard": {
        "id": None,
        "uid": "polar-performance-v5",
        "title": "Polar Performance",
        "tags": ["polar", "sport"],
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 1,
        "refresh": "5m",
        "time": {"from": "now-90d", "to": "now"},
        "panels": panels,
        "templating": {
            "list": [
                {
                    "type": "query",
                    "name": "sport",
                    "label": "Sport",
                    "datasource": DS,
                    "query": 'import "influxdata/influxdb/schema"\nschema.tagValues(bucket: "' + B + '", tag: "sport")',
                    "sort": 1,
                    "multi": True,
                    "includeAll": True,
                    "allValue": ".*",
                    "refresh": 2,
                    "current": {"text": "All", "value": "$__all"}
                }
            ]
        },
        "links": []
    },
    "overwrite": True,
    "folderUid": ""
}

# ── Envoi ────────────────────────────────────────────────────────────────────
headers = {"Authorization": f"Bearer {GRAFANA_API_KEY}", "Content-Type": "application/json"}
url = f"{GRAFANA_URL.rstrip('/')}/api/dashboards/db"
print("Envoi a Grafana...")

try:
    r = requests.post(url, json=dashboard, headers=headers, timeout=30)
    if r.status_code in [200, 201]:
        uid = r.json().get("uid", "polar-performance-v5")
        print(f"OK ! URL : {GRAFANA_URL}/d/{uid}")
    else:
        print(f"Erreur {r.status_code} : {r.text}")
except Exception as e:
    print(f"Exception : {e}")
