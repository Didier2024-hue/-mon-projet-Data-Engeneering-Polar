import os
import anthropic
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

ENV_PATH = "/home/datascientest/cde/polar/.env"
load_dotenv(ENV_PATH)

def query_influx(query):
    client = InfluxDBClient(
        url=os.getenv("INFLUX_URL"),
        token=os.getenv("INFLUX_TOKEN"),
        org=os.getenv("INFLUX_ORG")
    )
    query_api = client.query_api()
    result = query_api.query(query)
    return result

def analyze_with_claude(data_summary):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": f"""Tu es un coach sportif expert. Analyse ces données d'entraînement et donne des insights concis :

{data_summary}

Fournis :
1. Tendances principales
2. Points d'amélioration
3. Recommandations concrètes
"""
            }
        ]
    )
    return message.content[0].text

def get_recent_exercises():
    query = f'''
    from(bucket: "{os.getenv("INFLUX_BUCKET")}")
      |> range(start: -30d)
      |> filter(fn: (r) => r._measurement == "exercise")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    return query_influx(query)

if __name__ == "__main__":
    print("Récupération des données InfluxDB...")
    results = get_recent_exercises()
    
    # Formater les données pour Claude
    summary = "Données des 30 derniers jours :\n"
    for table in results:
        for record in table.records:
            summary += f"- {record['_time']} | Sport: {record.values.get('sport')} | Durée: {record.values.get('duration_sec')}s | Calories: {record.values.get('calories')} | FC moy: {record.values.get('hr_avg')} bpm\n"
    
    if summary == "Données des 30 derniers jours :\n":
        summary += "Aucune donnée disponible pour le moment."
    
    print("Analyse Claude en cours...")
    analysis = analyze_with_claude(summary)
    print("\n=== ANALYSE COACH ===")
    print(analysis)
