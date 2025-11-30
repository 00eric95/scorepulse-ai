import pandas as pd
import json
import os
import sys

# CONFIGURATION
EXCEL_PATH = 'epl_training_data.xlsx'
# We look for the CSV first as requested
CSV_PATH = 'epl_training_data.csv' 
OUTPUT_DIR = 'data'
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'current_team_stats.json')

def clean_col_name(col):
    # Standardize column names: remove spaces, convert to lowercase
    return col.strip().lower().replace(' ', '').replace('_', '')

def get_latest_stats(df):
    # Clean all column names to standard format (lowercase, no spaces)
    # e.g. "Home Team" -> "hometeam", "HomeTeam" -> "hometeam"
    df.columns = [clean_col_name(c) for c in df.columns]
    
    print(f"🔍 DEBUG: Normalized Columns: {list(df.columns)}")

    # Ensure sorting
    if 'date' in df.columns:
        # Handle multiple date formats safely
        df['date'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
        df = df.sort_values('date')
    
    # Get active teams
    recent_games = df.tail(380)
    
    # Find Home/Away columns reliably using normalized names
    if 'hometeam' in df.columns: home_col = 'hometeam'
    elif 'home' in df.columns: home_col = 'home'
    else: 
        print("❌ ERROR: Could not find Home Team column.")
        return {}

    if 'awayteam' in df.columns: away_col = 'awayteam'
    elif 'away' in df.columns: away_col = 'away'
    else:
        print("❌ ERROR: Could not find Away Team column.")
        return {}

    print(f"✅ Found columns: {home_col} vs {away_col}")

    teams = pd.concat([recent_games[home_col], recent_games[away_col]]).unique()
    print(f"✅ Found {len(teams)} active teams.")
    
    current_stats = {}
    
    # Identify target columns (goals)
    if 'fthg' in df.columns: 
        hg_col, ag_col = 'fthg', 'ftag'
    elif 'targethome' in df.columns:
        hg_col, ag_col = 'targethome', 'targetaway'
    else:
        print("⚠️ Warning: Goal columns not found. Using dummy 0 values.")
        hg_col, ag_col = None, None

    for team in teams:
        team_games = df[(df[home_col] == team) | (df[away_col] == team)].copy()
        last_5 = team_games.tail(5)
        
        if len(last_5) == 0: continue
            
        goals_scored = 0
        goals_conceded = 0
        points = 0
        
        if hg_col:
            for _, match in last_5.iterrows():
                is_home = match[home_col] == team
                h_goals = match[hg_col]
                a_goals = match[ag_col]
                
                # Skip if data is bad/NaN
                if pd.isna(h_goals) or pd.isna(a_goals): continue

                goals_scored += h_goals if is_home else a_goals
                goals_conceded += a_goals if is_home else h_goals
                
                if h_goals == a_goals: points += 1
                elif (is_home and h_goals > a_goals) or (not is_home and a_goals > h_goals): points += 3

        count = len(last_5)
        
        # Rank logic - Try to find any column containing 'rank'
        rank = 10
        rank_col_h = next((c for c in df.columns if 'hometeamrank' in c), None)
        rank_col_a = next((c for c in df.columns if 'awayteamrank' in c), None)
        
        if rank_col_h and rank_col_a:
             last_match = team_games.iloc[-1]
             rank = int(last_match[rank_col_h]) if last_match[home_col] == team else int(last_match[rank_col_a])
        
        current_stats[team] = {
            "rank": rank,
            "attack": round(goals_scored / count, 2),
            "defense": round(goals_conceded / count, 2),
            "form": round(points / count, 2)
        }
        
    return current_stats

if __name__ == "__main__":
    df = None
    # Priority 1: Read CSV
    if os.path.exists(CSV_PATH):
        print(f"📄 Reading CSV: {CSV_PATH}")
        try:
            df = pd.read_csv(CSV_PATH)
        except Exception as e:
            print(f"❌ Failed to read CSV: {e}")

    # Priority 2: Fallback to Excel
    elif os.path.exists(EXCEL_PATH):
        print(f"📄 Reading Excel: {EXCEL_PATH}")
        try:
            import openpyxl
            df = pd.read_excel(EXCEL_PATH)
        except:
            print("❌ Failed to read Excel.")
    
    else:
        print("❌ CRITICAL: Could not find data file.")

    if df is not None:
        if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
        stats = get_latest_stats(df)
        
        if stats:
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(stats, f, indent=4)
            print(f"🎉 SUCCESS! Saved {len(stats)} teams to {OUTPUT_FILE}")
        else:
            print("❌ ERROR: No stats generated (0 teams found). Check the DEBUG output above.")