import pandas as pd
import numpy as np
import joblib
import random
from sklearn.ensemble import RandomForestRegressor
from pathlib import Path

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Define Team Tiers (1 = Strongest, 5 = Weakest) to generate realistic synthetic data
# In the future, you will replace this with real historical CSV data.
TEAM_TIERS = {
    "Man City": 1, "Liverpool": 1, "Arsenal": 1,
    "Tottenham": 2, "Aston Villa": 2, "Man United": 2, "Newcastle": 2,
    "Chelsea": 3, "Brighton": 3, "West Ham": 3,
    "Brentford": 4, "Crystal Palace": 4, "Wolves": 4, "Fulham": 4, "Bournemouth": 4,
    "Everton": 4, "Nott'm Forest": 4,
    "Burnley": 5, "Sheffield Utd": 5, "Luton": 5
}

def generate_synthetic_data(num_matches=5000):
    """
    Generates match history based on team strength tiers.
    Tier 1 vs Tier 5 -> High chance of 3-0.
    Tier 3 vs Tier 3 -> High chance of 1-1.
    """
    print(f"🧠 Generating {num_matches} matches for training...")
    data = []
    teams = list(TEAM_TIERS.keys())

    for _ in range(num_matches):
        home = random.choice(teams)
        away = random.choice(teams)
        if home == away: continue

        home_str = 6 - TEAM_TIERS.get(home, 3) # Strength 1-5 (5 is best)
        away_str = 6 - TEAM_TIERS.get(away, 3)

        # Logic: Base Goals + Strength Diff + Home Advantage + Random Chaos
        home_advantage = 0.4
        strength_diff = (home_str - away_str) * 0.5
        
        home_exp = 1.2 + strength_diff + home_advantage + random.uniform(-0.5, 0.5)
        away_exp = 1.0 - strength_diff + random.uniform(-0.5, 0.5)

        # Ensure non-negative
        home_goals = max(0, int(round(home_exp)))
        away_goals = max(0, int(round(away_exp)))

        data.append({
            "home_team_code": hash(home) % 10000, # Simple numeric encoding
            "away_team_code": hash(away) % 10000,
            "home_tier": TEAM_TIERS.get(home, 3),
            "away_tier": TEAM_TIERS.get(away, 3),
            "home_goals": home_goals,
            "away_goals": away_goals
        })

    return pd.DataFrame(data)

def train():
    # 1. Get Data
    df = generate_synthetic_data()

    # 2. Define Features (X) and Targets (y)
    X = df[["home_team_code", "away_team_code", "home_tier", "away_tier"]]
    y_home = df["home_goals"]
    y_away = df["away_goals"]

    # 3. Train Models (Random Forest is great for tabular data)
    print("🏋️ Training Home Goals Model...")
    home_model = RandomForestRegressor(n_estimators=100, random_state=42)
    home_model.fit(X, y_home)

    print("🏋️ Training Away Goals Model...")
    away_model = RandomForestRegressor(n_estimators=100, random_state=42)
    away_model.fit(X, y_away)

    # 4. Save Models
    joblib.dump(home_model, MODEL_DIR / "home_goals_model.pkl")
    joblib.dump(away_model, MODEL_DIR / "away_goals_model.pkl")
    
    print("✅ Models Saved Successfully in src/models/")

if __name__ == "__main__":
    train()