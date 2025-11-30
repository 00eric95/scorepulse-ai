import os
import requests
import time
from pathlib import Path
import urllib.parse

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
BADGES_DIR = STATIC_DIR / "badges"

# Create directories if they don't exist
BADGES_DIR.mkdir(parents=True, exist_ok=True)

# Map "Our Team Name" -> List of "Wikipedia File Names" to try
# We use lists to provide fallbacks. If the first link is dead, it tries the next.
WIKI_FILES = {
    "Arsenal": ["Arsenal_FC.svg"],
    "Aston Villa": ["Aston_Villa_FC_crest_(2016).svg", "Aston_Villa_FC_logo.svg"],
    "Bournemouth": ["AFC_Bournemouth_(2013).svg", "AFC_Bournemouth.svg"],
    "Brentford": ["Brentford_FC_crest.svg", "Brentford_FC_logo.svg"],
    "Brighton": ["Brighton_&_Hove_Albion_logo.svg", "Brighton_and_Hove_Albion_FC_logo.svg"],
    "Burnley": ["Burnley_F.C._Logo.png", "Burnley_FC_badge.png", "Burnley_Football_Club_Logo.png"], 
    "Chelsea": ["Chelsea_FC.svg"],
    "Crystal Palace": ["Crystal_Palace_FC_logo_(2022).svg", "Crystal_Palace_F.C._logo_(2022).svg", "Crystal_Palace_FC_logo.svg"],
    "Everton": ["Everton_FC_logo.svg"],
    "Fulham": ["Fulham_FC_(shield).svg", "Fulham_FC_logo.svg"],
    "Liverpool": ["Liverpool_FC.svg"],
    "Luton": ["Luton_Town_logo.svg", "Luton_Town_FC_logo.svg"],
    "Man City": ["Manchester_City_FC_badge.svg", "Manchester_City_logo.svg"],
    "Man United": ["Manchester_United_FC_crest.svg", "Manchester_United_logo.svg"],
    "Newcastle": ["Newcastle_United_Logo.svg", "Newcastle_United_FC_logo.svg"],
    "Nott'm Forest": ["Nottingham_Forest_F.C._logo.svg", "Nottingham_Forest_logo.svg"],
    "Sheffield Utd": ["Sheffield_United_FC_logo.svg"],
    "Tottenham": ["Tottenham_Hotspur.svg", "Tottenham_Hotspur_FC_logo.svg"],
    "West Ham": ["West_Ham_United_FC_logo.svg"],
    "Wolves": ["Wolverhampton_Wanderers.svg", "Wolverhampton_Wanderers_FC_logo.svg"]
}

def download_badges():
    print(f"⬇️  Downloading badges to: {BADGES_DIR}")
    print("-" * 50)
    
    # Use a real browser User-Agent to avoid getting blocked (ConnectionResetError)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    success_count = 0
    session = requests.Session()
    
    for team_name, candidates in WIKI_FILES.items():
        # Determine local save path
        save_name = f"{team_name.replace(' ', '_')}.svg"
        if "Burnley" in team_name: save_name = "Burnley.png"
        
        save_path = BADGES_DIR / save_name
        
        # Skip if already exists
        if save_path.exists():
            print(f"✅ {team_name} already exists.")
            success_count += 1
            continue

        # Try each candidate URL until one works
        saved = False
        for wiki_filename in candidates:
            url = f"https://en.wikipedia.org/wiki/Special:FilePath/{urllib.parse.quote(wiki_filename)}"
            try:
                print(f"⏳ Fetching {team_name}...", end=" ", flush=True)
                
                # Add a small delay to be polite and avoid server-side resets
                time.sleep(1)
                
                response = session.get(url, headers=headers, allow_redirects=True, timeout=15)
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'image' not in content_type and 'xml' not in content_type:
                        print(f"❌ (Not an image: {content_type})")
                        continue

                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    print(f"✅ Success!")
                    saved = True
                    success_count += 1
                    break # Stop trying candidates for this team
                else:
                    print(f"❌ (Status {response.status_code})")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        if not saved:
            print(f"⚠️  COULD NOT DOWNLOAD BADGE FOR: {team_name}")

    print("-" * 50)
    print(f"🎉 Process Complete. Downloaded {success_count}/{len(WIKI_FILES)} badges.")
    print("👉 Restart your server to see the changes.")

if __name__ == "__main__":
    download_badges()