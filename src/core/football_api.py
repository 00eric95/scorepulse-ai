import requests
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
CACHE_FILE = BASE_DIR / "fixtures_cache.json"
CACHE_DURATION_HOURS = 6

# 🚨 TROUBLESHOOTING SWITCH 🚨
FORCE_MOCK_MODE = False 

# 🔑 YOUR API CONFIGURATION
API_KEY = "ca08b1f49234498bbfb2dfbcd7b68c2e"
API_HOST = "api-football-v1.p.rapidapi.com"
LEAGUE_ID = 39  # Premier League
SEASON = 2024   # Current Season

NAME_MAP = {
    "Manchester United": "Man_United",
    "Manchester City": "Man_City",
    "Nottingham Forest": "Nott'm_Forest",
    "Sheffield United": "Sheffield_Utd",
    "Wolverhampton": "Wolves",
    "West Ham": "West_Ham",
    "Tottenham": "Tottenham",
    "Brighton": "Brighton",
    "Leeds United": "Leeds",
    "Leicester City": "Leicester"
}

def get_upcoming_fixtures():
    if FORCE_MOCK_MODE:
        print("⚠️ Force Mock Mode Enabled.")
        return get_mock_fixtures()

    cached_data = load_from_cache()
    if cached_data:
        print("⚡ Using Cached Fixtures")
        return cached_data

    print("⚽ Connecting to RapidAPI...")
    
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    today = datetime.now().strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    querystring = {
        "league": LEAGUE_ID,
        "season": SEASON,
        "from": today,
        "to": next_week,
        "status": "NS"
    }

    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": API_HOST
    }

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=5)
        data = response.json()
        
        # ✅ FIX: Check for errors safely
        if "errors" in data and data["errors"]:
            print(f"⚠️ API Error Response: {data['errors']}")
            return get_mock_fixtures()
            
        # ✅ FIX: Safely get 'results' count
        results_count = data.get("results", 0)
        
        # Sometimes API returns 'message' on quota limit without 'errors' key
        if "message" in data and not results_count:
             print(f"⚠️ API Message: {data['message']}")

        if results_count == 0:
            print("ℹ️ No live matches found or API issue. Using mock data.")
            return get_mock_fixtures()

        fixtures = []
        # ✅ FIX: Safely iterate response
        match_list = data.get("response", [])
        
        for match in match_list:
            match_dt = datetime.fromisoformat(match["fixture"]["date"].replace("Z", "+00:00"))
            
            fixtures.append({
                "id": match["fixture"]["id"],
                "home": match["teams"]["home"]["name"],
                "away": match["teams"]["away"]["name"],
                "date": match_dt.strftime("%Y-%m-%d"),
                "time": match_dt.strftime("%H:%M"),
                "venue": match["fixture"]["venue"]["name"] or "Unknown Stadium"
            })
            
        save_to_cache(fixtures)
        print(f"✅ Loaded & Cached {len(fixtures)} live matches.")
        return fixtures

    except Exception as e:
        print(f"❌ API Connection Failed: {e}")
        print("👉 Switching to Mock Data.")
        return get_mock_fixtures()

def load_from_cache():
    if not CACHE_FILE.exists(): return None
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
        if time.time() - cache.get("timestamp", 0) < (CACHE_DURATION_HOURS * 3600):
            return cache.get("data")
        return None
    except Exception: return None

def save_to_cache(data):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "data": data}, f)
    except Exception as e:
        print(f"⚠️ Write cache failed: {e}")

def get_mock_fixtures():
    today = datetime.now()
    date_tom = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    return [
        {"id": 101, "home": "Arsenal", "away": "Man City", "date": date_tom, "time": "14:30", "venue": "Emirates Stadium"},
        {"id": 102, "home": "Liverpool", "away": "Chelsea", "date": date_tom, "time": "17:00", "venue": "Anfield"},
        {"id": 103, "home": "Man United", "away": "Tottenham", "date": (today + timedelta(days=2)).strftime("%Y-%m-%d"), "time": "16:00", "venue": "Old Trafford"},
    ]

def get_team_logo(team_name):
    if not team_name: return ""
    base_name = NAME_MAP.get(team_name, team_name.replace(" ", "_"))
    if "Burnley" in team_name: return f"/static/badges/{base_name}.png"
    return f"/static/badges/{base_name}.svg"