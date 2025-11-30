import joblib
import pandas as pd
from pathlib import Path
import random

# --- CONFIGURATION ---
# This must match the path where train_model.py saves files
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR.parent / "models"

# Load Models (Global to avoid reloading on every request)
try:
    HOME_MODEL = joblib.load(MODEL_DIR / "home_goals_model.pkl")
    AWAY_MODEL = joblib.load(MODEL_DIR / "away_goals_model.pkl")
    print("✅ AI Models Loaded Successfully")
except Exception as e:
    print(f"⚠️ Warning: Could not load models. Using fallback logic. ({e})")
    # If models aren't found, these remain None and trigger fallback below
    HOME_MODEL = None
    AWAY_MODEL = None

# Team Tiers (Must match training script for correct encoding)
# 1 = Strongest, 5 = Weakest
TEAM_TIERS = {
    "Man City": 1, "Liverpool": 1, "Arsenal": 1,
    "Tottenham": 2, "Aston Villa": 2, "Man United": 2, "Newcastle": 2,
    "Chelsea": 3, "Brighton": 3, "West Ham": 3,
    "Brentford": 4, "Crystal Palace": 4, "Wolves": 4, "Fulham": 4, "Bournemouth": 4,
    "Everton": 4, "Nott'm Forest": 4,
    "Burnley": 5, "Sheffield Utd": 5, "Luton": 5
}

def predict_match_score(home_team, away_team):
    """
    Predicts the score using the trained Random Forest models.
    """
    # 1. Fallback if models missing (e.g., training script hasn't run yet)
    if not HOME_MODEL or not AWAY_MODEL:
        return random_fallback(home_team, away_team)

    # 2. Prepare Input Features (Must match training features exactly)
    input_data = pd.DataFrame([{
        "home_team_code": hash(home_team) % 10000,
        "away_team_code": hash(away_team) % 10000,
        # Default to Tier 3 (Mid-table) if team name isn't in our list
        "home_tier": TEAM_TIERS.get(home_team, 3), 
        "away_tier": TEAM_TIERS.get(away_team, 3)
    }])

    # 3. Predict
    # The model returns a float (e.g., 2.4 goals), so we round it
    home_pred = HOME_MODEL.predict(input_data)[0]
    away_pred = AWAY_MODEL.predict(input_data)[0]

    # 4. Add slight variance ("The Ball is Round" factor)
    # Real football isn't perfectly deterministic. We add +/- 0.2 variance
    # This ensures 2.4 might become 2 or 3, adding realism.
    home_pred += random.uniform(-0.2, 0.2)
    away_pred += random.uniform(-0.2, 0.2)

    return int(round(home_pred)), int(round(away_pred))

def random_fallback(home, away):
    """Legacy random logic for fallback if models crash or are missing"""
    print(f"⚠️ Using random fallback for {home} vs {away}")
    return random.randint(0, 3), random.randint(0, 2)