import pandas as pd
import json
import os
from datetime import datetime

# Define paths
DATA_PATH = 'epl_training_data.csv' # Input (Historical Data)
OUTPUT_DIR = 'src/data'
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'current_team_stats.json')

def get_latest_stats(df):
    """
    Calculates the most recent form, attack, and defense stats for every team 
    based on the very last matches they played in the dataset.
    """
    # Ensure sorting
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Get list of all unique teams in the current season (assumes dataset has recent games)
    # We look at the last 380 rows (approx 1 season) to find active teams
    recent_games = df.tail(380)
    teams = pd.concat([recent_games['home_team'], recent_games['away_team']]).unique()
    
    current_stats = {}
    
    print(f"Calculating current stats for {len(teams)} teams...")
    
    for team in teams:
        # 1. Filter for games involving this team
        team_games = df[(df['home_team'] == team) | (df['away_team'] == team)].copy()
        
        # 2. Get the Last 5 Games (The "Form" Window)
        last_5 = team_games.tail(5)
        
        if len(last_5) == 0:
            continue
            
        # 3. Calculate Metrics
        goals_scored = 0
        goals_conceded = 0
        points = 0
        
        for _, match in last_5.iterrows():
            is_home = match['home_team'] == team
            
            # Goals
            goals_scored += match['TARGET_HOME'] if is_home else match['TARGET_AWAY']
            goals_conceded += match['TARGET_AWAY'] if is_home else match['TARGET_HOME']
            
            # Points Calculation
            home_goals = match['TARGET_HOME']
            away_goals = match['TARGET_AWAY']
            
            if home_goals == away_goals:
                points += 1 # Draw
            elif is_home and home_goals > away_goals:
                points += 3 # Win
            elif not is_home and away_goals > home_goals:
                points += 3 # Win
        
        # Averages
        games_count = len(last_5)
        avg_goals = round(goals_scored / games_count, 2)
        avg_conceded = round(goals_conceded / games_count, 2)
        avg_form = round(points / games_count, 2)
        
        # Get Latest Ranking (from the last match they played)
        last_match = team_games.iloc[-1]
        if last_match['home_team'] == team:
            rank = int(last_match['home_team_ranking'])
        else:
            rank = int(last_match['away_team_ranking'])
            
        # 4. Store in Dictionary
        current_stats[team] = {
            "rank": rank,
            "attack": avg_goals,   # Corresponds to rolling_goals
            "defense": avg_conceded, # Corresponds to rolling_defense
            "form": avg_form       # Corresponds to rolling_points
        }
        
    return current_stats

def main():
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # Load Data
    if not os.path.exists(DATA_PATH):
        print(f"Error: {DATA_PATH} not found. Run generate_epl_data.py first.")
        return

    df = pd.read_csv(DATA_PATH)
    
    # Calculate
    stats = get_latest_stats(df)
    
    # Save to JSON
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(stats, f, indent=4)
        
    print(f"Success! Current stats exported to {OUTPUT_FILE}")
    print("Example (Arsenal):", stats.get('Arsenal', 'Not Found'))

if __name__ == "__main__":
    main()