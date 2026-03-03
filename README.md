# 🏋️ Polar Coach AI

> An intelligent sports coaching and analysis system powered by Polar Flow data, InfluxDB, Grafana and Claude AI.

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-green)
![InfluxDB](https://img.shields.io/badge/InfluxDB-2.x-orange)
![Grafana](https://img.shields.io/badge/Grafana-10.x-red)
![Claude](https://img.shields.io/badge/Claude-Sonnet-purple)

---

## 📋 Overview

Polar Coach AI is a complete data pipeline that:
- Fetches training data from **Polar Flow** (historical export + real-time via AccessLink API)
- Stores it in **InfluxDB** (time-series database)
- Visualizes it in **Grafana** (interactive dashboard)
- Analyzes it with **Claude AI** via a web chatbot with integrated charts

---

## 🏗️ Architecture

```
Polar Flow / AccessLink API
        ↓
  ETL Python (utils/)
        ↓
    InfluxDB
     ↙     ↘
Grafana    Flask + Claude API
Dashboard   AI Coach Chatbot
```

---

## 📁 Project Structure

```
polar/
├── polar_coach.sh              # 🚀 Main launcher script
├── api/
│   └── polar_exercises.py      # Fetch new sessions via AccessLink
├── utils/
│   ├── 01_pre_ingest_polar_training.py         # JSONL preparation
│   ├── 02_supp_anomalies_fichier_historique.py # Data cleaning
│   ├── 03_delete_bucket.py                     # InfluxDB bucket purge
│   ├── 04_ingest_polar_final.py                # Historical data ingestion
│   ├── 05_post_ingest_polar_training.py        # Quality control
│   └── 06_generate_grafana_dashboard.py        # Grafana dashboard generation
├── mcp/
│   ├── polar_mcp_server.py     # MCP server (Claude tools)
│   └── test_mcp_server.py      # MCP function tests
├── flask/
│   ├── app.py                  # Flask backend + Claude API
│   └── templates/
│       └── index.html          # Web chatbot interface
├── claude/
│   └── chatbot_polar.py        # Command-line chatbot
├── data/
│   └── extracted/              # JSON session files
└── .env                        # Configuration (not committed)
```

---

## ⚙️ Installation

### Prerequisites
- Python 3.10+
- InfluxDB 2.x
- Grafana 10.x
- Polar Flow account + registered AccessLink app
- Anthropic API key (Claude)

### 1. Clone the repository
```bash
git clone <repo_url>
cd polar
```

### 2. Create virtual environment
```bash
python3 -m venv pol
source pol/bin/activate
pip install -r requirements.txt
```

### 3. Configure `.env`
```bash
cp .env.example .env
# Edit with your values
```

Required variables:
```env
# Polar AccessLink
POLAR_ACCESS_TOKEN=your_token
POLAR_USER_ID=your_user_id

# InfluxDB
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=your_influx_token
INFLUX_ORG=your_org
INFLUX_BUCKET=polar_metrics

# Grafana
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=your_grafana_key

# Claude API
ANTHROPIC_API_KEY=sk-ant-your_key
```

---

## 🚀 Initial Pipeline (historical data)

Run once to load your Polar history:

```bash
source pol/bin/activate

# 1. Extract Polar Flow ZIP into data/extracted/
# 2. Prepare JSONL files
python3 utils/01_pre_ingest_polar_training.py

# 3. Clean anomalies
python3 utils/02_supp_anomalies_fichier_historique.py

# 4. Purge InfluxDB bucket (if reloading)
python3 utils/03_delete_bucket.py

# 5. Ingest into InfluxDB
python3 utils/04_ingest_polar_final.py

# 6. Quality control
python3 utils/05_post_ingest_polar_training.py

# 7. Generate Grafana dashboard
python3 utils/06_generate_grafana_dashboard.py
```

---

## 📅 Daily Usage

A single command does everything:

```bash
cd /home/datascientest/cde/polar
./polar_coach.sh
```

This script:
1. 📡 Fetches new sessions via AccessLink
2. 💾 Saves them as JSON in `data/extracted/`
3. 📊 Ingests them into InfluxDB
4. 🌐 Displays interface URLs

---

## 🌐 Interfaces

| Interface | URL | Description |
|-----------|-----|-------------|
| 🤖 Polar Coach AI | `http://<IP>:5001` | Claude chatbot + charts |
| 📊 Grafana | `http://<IP>:3000` | Real-time dashboard |

---

## 🤖 Polar Coach AI - Features

The chatbot analyzes your training data in natural language:

- **"Analyze my progress this month"**
- **"Am I overtraining?"**
- **"Tips to improve my heart rate"**
- **"Training plan for next week"**
- **"Summarize my swimming performance"**

### Available Claude Tools

| Tool | Description |
|------|-------------|
| `get_recent_sessions` | Latest sessions with all metrics |
| `get_stats_by_sport` | Average stats per sport |
| `get_weekly_load` | Weekly training load |
| `get_hr_zones` | Heart rate zones by sport |
| `get_user_profile` | Athlete profile |

---

## 📊 Grafana Dashboard

Available panels:
- **KPIs**: Sessions, Distance, Calories, Time, Avg HR, Max HR
- **Distance by sport** (timeseries)
- **Average HR by sport** (timeseries)
- **Calories by sport** (timeseries)
- **Duration by sport** (timeseries)
- **Last 50 sessions history** (table)

Dynamic filter by sport.

---

## 🔧 Systemd Service

The Flask interface starts automatically at boot:

```bash
# Status
sudo systemctl status polar-coach

# Restart
sudo systemctl restart polar-coach

# Logs
sudo journalctl -u polar-coach -f
```

---

## 📦 Main Dependencies

```
anthropic
flask
flask-cors
influxdb-client
plotly
python-dotenv
requests
mcp
```

---

## 🗺️ Roadmap

v1
Polar Flow ingestion
Grafana dashboards

v2
AI training insights

v3
Fatigue prediction model

v4
Training recommendation system

---

## 👤 Author

**kiemberaid** — Personal data science project applied to sports performance

---

## 📄 License

MIT License
