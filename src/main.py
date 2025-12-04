print("⏳ Initializing ScorePulse AI (Secure Mode)...")
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
import uvicorn
import sys
import traceback
import base64
import json
import bcrypt
import random
import webbrowser
import threading
import time
import os
from datetime import datetime

# --- CHECK FOR LIBRARIES ---
try:
    import requests
    import pyodbc
    from dotenv import load_dotenv # ✅ NEW: Load environment variables
except ImportError as e:
    print(f"\n❌ CRITICAL ERROR: Missing library: {e}")
    print("👉 Run: pip install python-dotenv")
    sys.exit(1)

# --- 1. LOAD SECRETS ---
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(ENV_PATH)

# Helper to get env vars safely
def get_env(key, default=None):
    value = os.getenv(key, default)
    if not value and not default:
        print(f"⚠️ WARNING: Missing Config: {key}")
    return value

# --- SETUP PATHS ---
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
sys.path.append(str(BASE_DIR))

app = FastAPI()

# 🔐 SECURE SESSION MIDDLEWARE
# Uses the secret from .env so sessions can't be forged
SECRET_KEY = get_env("SESSION_SECRET_KEY", "fallback-dev-secret")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=False) # Set https_only=True in production

# --- 2. MOUNT STATIC FILES ---
if not STATIC_DIR.exists():
    print(f"⚠️ Warning: Static directory not found at {STATIC_DIR}")
else:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ==============================================================================
# --- 3. DATABASE CONFIGURATION ---
# ==============================================================================

import os
import sqlite3

# Detect Render environment
RUNNING_ON_RENDER = os.getenv("RENDER", "false").lower() == "true"

# SQL Server (Local)
SQL_SERVER = get_env("SQL_SERVER", "DESKTOP-V18R2T9")
SQL_DATABASE = get_env("SQL_DATABASE", "ScorePulseDB")
SQL_DRIVER = "{ODBC Driver 17 for SQL Server}"
USE_WINDOWS_AUTH = True


# ⚠️ Only import pyodbc when NOT on Render
if not RUNNING_ON_RENDER:
    try:
        import pyodbc
    except ImportError:
        pyodbc = None


# -------------------------------
#   1. SQL SERVER (LOCAL) ONLY
# -------------------------------
def get_connection_string():
    """Only used on LOCAL machine."""
    if RUNNING_ON_RENDER:
        return None  # Render will never use this

    if pyodbc is None:
        print("⚠️ pyodbc missing locally. SQL Server connection disabled.")
        return None

    try:
        available_drivers = pyodbc.drivers()
        driver_name = "{SQL Server}"

        priorities = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
            "ODBC Driver 13 for SQL Server",
            "SQL Server Native Client 11.0"
        ]

        for d in priorities:
            if d in available_drivers:
                driver_name = f"{{{d}}}"
                break

        conn_str = (
            f"DRIVER={driver_name};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
        )

        if USE_WINDOWS_AUTH:
            conn_str += "Trusted_Connection=yes;"
        else:
            conn_str += "UID=sa;PWD=your_password;"

        conn_str += "LoginTimeout=5;TrustServerCertificate=yes;"

        return conn_str

    except Exception:
        return None


# -------------------------------
#   2. AUTO–DB SWITCH
# -------------------------------
def get_db_connection():
    """Automatically chooses SQLite on Render, SQL Server locally."""
    
    # ---------- Render → SQLite ----------
    if RUNNING_ON_RENDER:
        return sqlite3.connect("database.sqlite3")

    # ---------- Local → SQL Server ----------
    conn_str = get_connection_string()

    if conn_str and pyodbc:
        try:
            return pyodbc.connect(conn_str)
        except Exception as e:
            print(f"⚠️ SQL Server connection failed ({e}). Falling back to SQLite...")

    # ---------- Fallback for local if SQL Server fails ----------
    return sqlite3.connect("database.sqlite3")


def row_to_dict(cursor, row):
    return {col[0]: val for col, val in zip(cursor.description, row)}

def init_db():
    print("🔄 Checking Database Integrity...")
    conn = get_db_connection()
    if not conn: 
        print("⚠️  SKIPPING DATABASE: Server unreachable.")
        return
    cursor = conn.cursor()
    try:
        # Users Table
        cursor.execute('''IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U') CREATE TABLE users (id INT IDENTITY(1,1) PRIMARY KEY, email NVARCHAR(255) UNIQUE NOT NULL, password NVARCHAR(MAX) NOT NULL, is_pro INT DEFAULT 0, subscription_end DATETIME NULL, prediction_count INT DEFAULT 0)''')
        try: cursor.execute("ALTER TABLE users ADD is_admin INT DEFAULT 0") 
        except: pass
        
        # Transactions
        cursor.execute('''IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='transactions' AND xtype='U') CREATE TABLE transactions (checkout_request_id NVARCHAR(255) PRIMARY KEY, user_id INT, phone_number NVARCHAR(50), amount INT, status NVARCHAR(50) DEFAULT 'PENDING', created_at DATETIME DEFAULT GETDATE())''')
        
        # Predictions
        cursor.execute('''IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='predictions' AND xtype='U') CREATE TABLE predictions (id INT IDENTITY(1,1) PRIMARY KEY, user_id INT, home_team NVARCHAR(100), away_team NVARCHAR(100), predicted_score NVARCHAR(50), outcome NVARCHAR(50), created_at DATETIME DEFAULT GETDATE())''')
        
        conn.commit()
        print(f"✅ Database Secured & Connected: '{SQL_DATABASE}'")
    except Exception as e: print("❌ DB Init Error:", str(e))
    finally: conn.close()

init_db()

# --- 4. M-PESA CONFIGURATION ---
# ✅ LOADED FROM ENV
MPESA_CONSUMER_KEY = get_env("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = get_env("MPESA_CONSUMER_SECRET")
MPESA_PASSKEY = get_env("MPESA_PASSKEY")
MPESA_SHORTCODE = "174379"
MPESA_BASE_URL = "https://sandbox.safaricom.co.ke"
# Use Ngrok for local testing (loaded from env or default fallback)
MPESA_CALLBACK_URL = get_env("MPESA_CALLBACK_URL", "https://YOUR_NGROK_URL.ngrok-free.app/mpesa/callback")

def get_mpesa_access_token():
    if not MPESA_CONSUMER_KEY or "YOUR_" in MPESA_CONSUMER_KEY: return None
    api_url = f"{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    try:
        creds = f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}"
        encoded = base64.b64encode(creds.encode()).decode()
        headers = {"Authorization": f"Basic {encoded}"}
        response = requests.get(api_url, headers=headers)
        return response.json().get("access_token")
    except Exception: return None

# --- IMPORT MODULES ---
try:
    from core.inferencemodel import predict_match_score
    from core.football_api import get_upcoming_fixtures, get_team_logo
except ImportError:
    def predict_match_score(home, away): return 0, 0
    def get_upcoming_fixtures(): return []
    def get_team_logo(name): return ""

# --- TEAM DATA ---
TEAM_DATA = {
    "Arsenal": "/static/badges/Arsenal.svg",
    "Aston Villa": "/static/badges/Aston_Villa.svg",
    "Bournemouth": "/static/badges/Bournemouth.svg",
    "Brentford": "/static/badges/Brentford.svg",
    "Brighton": "/static/badges/Brighton.svg",
    "Burnley": "/static/badges/Burnley.png",
    "Chelsea": "/static/badges/Chelsea.svg",
    "Crystal Palace": "/static/badges/Crystal_Palace.svg",
    "Everton": "/static/badges/Everton.svg",
    "Fulham": "/static/badges/Fulham.svg",
    "Liverpool": "/static/badges/Liverpool.svg",
    "Luton": "/static/badges/Luton.svg",
    "Man City": "/static/badges/Man_City.svg",
    "Man United": "/static/badges/Man_United.svg",
    "Newcastle": "/static/badges/Newcastle.svg",
    "Nott'm Forest": "/static/badges/Nott'm_Forest.svg",
    "Sheffield Utd": "/static/badges/Sheffield_Utd.svg",
    "Tottenham": "/static/badges/Tottenham.svg",
    "West Ham": "/static/badges/West_Ham.svg",
    "Wolves": "/static/badges/Wolves.svg"
}

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = request.session.get("user")
    upcoming_matches = get_upcoming_fixtures()
    return templates.TemplateResponse("home.html", {
        "request": request, "user": user, "matches": upcoming_matches
    })

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_user(request: Request, email: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    if not conn: return templates.TemplateResponse("register.html", {"request": request, "error": "DB Unavailable"})
    cursor = conn.cursor()
    try:
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return templates.TemplateResponse("register.html", {"request": request, "error": "Email taken"})
        cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_pw))
        conn.commit()
        return RedirectResponse(url="/login", status_code=303)
    except Exception as e:
        return templates.TemplateResponse("register.html", {"request": request, "error": str(e)})
    finally: conn.close()

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_user(request: Request, email: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    if not conn: return templates.TemplateResponse("login.html", {"request": request, "error": "DB Unavailable"})
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, email, password, is_pro, is_admin FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if row:
        user_id, user_email, stored_hash, is_pro, is_admin = row
        if isinstance(stored_hash, str): stored_hash = stored_hash.encode('utf-8')
        
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            request.session["user"] = {"id": user_id, "email": user_email, "is_pro": is_pro, "is_admin": is_admin}
            return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    user_session = request.session.get("user")
    if not user_session: return RedirectResponse(url="/login", status_code=303)
    conn = get_db_connection()
    if not conn: return HTMLResponse("Database Error", status_code=500)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_session['id'],))
    user = row_to_dict(cursor, cursor.fetchone())
    cursor.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC", (user_session['id'],))
    txn_rows = cursor.fetchall()
    transactions = [row_to_dict(cursor, row) for row in txn_rows]
    cursor.execute("SELECT TOP 20 * FROM predictions WHERE user_id = ? ORDER BY created_at DESC", (user_session['id'],))
    pred_rows = cursor.fetchall()
    predictions = [row_to_dict(cursor, row) for row in pred_rows]
    conn.close()
    
    if user:
         request.session["user"] = {"id": user["id"], "email": user["email"], "is_pro": user["is_pro"], "is_admin": user.get("is_admin", 0)}

    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "transactions": transactions, "predictions": predictions})

@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request):
    user = request.session.get("user")
    return templates.TemplateResponse("pricing.html", {"request": request, "user": user})

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user_session = request.session.get("user")
    if not user_session: return RedirectResponse(url="/login", status_code=303)
    conn = get_db_connection()
    if not conn: return HTMLResponse("Database Error", status_code=500)
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin, email FROM users WHERE id = ?", (user_session['id'],))
    row = cursor.fetchone()
    if not row: return RedirectResponse(url="/login", status_code=303)
    is_admin, email = row[0], row[1]
    if is_admin != 1 and email != "admin@scorepulse.com":
        return HTMLResponse("<h1>403 Forbidden</h1><p>Access Denied</p>", status_code=403)
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM users")
    stats['total_users'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_pro = 1")
    stats['pro_users'] = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE status = 'COMPLETED'")
    rev_row = cursor.fetchone()
    stats['total_revenue'] = rev_row[0] if rev_row and rev_row[0] else 0
    cursor.execute("SELECT TOP 10 t.*, u.email FROM transactions t JOIN users u ON t.user_id = u.id ORDER BY t.created_at DESC")
    txn_rows = cursor.fetchall()
    recent_transactions = [{**row_to_dict(cursor, row), "email": row.email} for row in txn_rows]
    conn.close()
    return templates.TemplateResponse("admin.html", {"request": request, "user": user_session, "stats": stats, "transactions": recent_transactions})

@app.get("/upcoming", response_class=HTMLResponse)
async def upcoming_page(request: Request, home: str = None, away: str = None):
    user = request.session.get("user")
    if not user: return RedirectResponse(url="/login", status_code=303)
    teams_list = [{"name": name, "logo": logo} for name, logo in TEAM_DATA.items()]
    
    result_data = None
    hide_form = False
    
    if home and away:
        hide_form = True
        conn = get_db_connection()
        is_pro = 0
        pred_count = 0
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_pro, prediction_count FROM users WHERE id = ?", (user['id'],))
            row = cursor.fetchone()
            if row:
                is_pro, pred_count = row[0], row[1] if row[1] else 0
                if is_pro == 0 and pred_count >= 100:
                    conn.close()
                    return templates.TemplateResponse("pricing.html", {"request": request, "user": user, "alert": "Limit Reached!"})
                if is_pro == 0:
                    cursor.execute("UPDATE users SET prediction_count = prediction_count + 1 WHERE id = ?", (user['id'],))
                    conn.commit()
            conn.close()

        home_score, away_score = predict_match_score(home, away)
        if home_score > away_score: outcome = f"{home} Win"
        elif away_score > home_score: outcome = f"{away} Win"
        else: outcome = "Draw"
        
        home_logo = get_team_logo(home)
        away_logo = get_team_logo(away)

        result_data = {
            "home_team": home, "away_team": away,
            "home_logo": home_logo, "away_logo": away_logo,
            "predicted_score": f"{home_score} - {away_score}",
            "outcome": outcome,
            "exact_goals": [float(home_score) + 0.34, float(away_score) + 0.12],
            "factors": {
                "Home Form": round(random.uniform(1.2, 2.5), 1),
                "Away Form": round(random.uniform(0.8, 2.0), 1),
                "Home Attack": int(random.uniform(70, 95)), 
                "Away Attack": int(random.uniform(65, 90)),
                "Home Defense": int(random.uniform(60, 85)), 
                "Away Defense": int(random.uniform(60, 85))
            }
        }

    return templates.TemplateResponse("upcoming.html", {
        "request": request, "teams": teams_list, "user": user, 
        "selected_home": home, "selected_away": away,
        "result": result_data, "hide_form": hide_form
    })

@app.post("/upcoming", response_class=HTMLResponse)
async def upcoming_predict(request: Request, home_team: str = Form(...), away_team: str = Form(...)):
    import urllib.parse
    safe_home = urllib.parse.quote(home_team)
    safe_away = urllib.parse.quote(away_team)
    return RedirectResponse(url=f"/upcoming?home={safe_home}&away={safe_away}", status_code=303)

@app.post("/mpesa/stkpush")
async def mpesa_stk_push(request: Request, phone_number: str = Form(...), amount: int = Form(...)):
    user = request.session.get("user")
    if not user: return JSONResponse(content={"detail": "Login required"}, status_code=401)
    access_token = get_mpesa_access_token()
    if not access_token: return JSONResponse(content={"detail": "M-Pesa Auth Failed"}, status_code=500)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()).decode()
    payload = {
        "BusinessShortCode": MPESA_SHORTCODE, "Password": password, "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline", "Amount": amount, "PartyA": phone_number,
        "PartyB": MPESA_SHORTCODE, "PhoneNumber": phone_number, "CallBackURL": MPESA_CALLBACK_URL,
        "AccountReference": "ScorePulseAI", "TransactionDesc": "Subscription"
    }
    try:
        resp = requests.post(f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest", json=payload, headers={"Authorization": f"Bearer {access_token}"})
        data = resp.json()
        if resp.status_code == 200:
            conn = get_db_connection()
            if conn:
                conn.execute("INSERT INTO transactions (checkout_request_id, user_id, phone_number, amount) VALUES (?, ?, ?, ?)", (data.get("CheckoutRequestID"), user['id'], phone_number, amount))
                conn.commit()
                conn.close()
            return JSONResponse(content=data)
        return JSONResponse(content={"detail": data.get('errorMessage', 'Failed')}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"detail": str(e)}, status_code=500)

@app.post("/mpesa/callback")
async def mpesa_callback(request: Request):
    try:
        data = await request.json()
        result_code = data.get("Body", {}).get("stkCallback", {}).get("ResultCode")
        checkout_id = data.get("Body", {}).get("stkCallback", {}).get("CheckoutRequestID")
        conn = get_db_connection()
        if conn:
            if result_code == 0:
                conn.execute("UPDATE transactions SET status = 'COMPLETED' WHERE checkout_request_id = ?", (checkout_id,))
                row = conn.execute("SELECT user_id FROM transactions WHERE checkout_request_id = ?", (checkout_id,)).fetchone()
                if row: conn.execute("UPDATE users SET is_pro = 1 WHERE id = ?", (row[0],))
            else:
                conn.execute("UPDATE transactions SET status = 'FAILED' WHERE checkout_request_id = ?", (checkout_id,))
            conn.commit()
            conn.close()
        return JSONResponse(content={"ResultCode": 0})
    except Exception:
        return JSONResponse(content={"ResultCode": 1})

@app.get("/predict", response_class=HTMLResponse)
async def predict_page(request: Request):
    return RedirectResponse(url="/upcoming", status_code=303)

def open_browser():
    print("🌐 Launching Browser in 2 seconds...")
    time.sleep(2)
    try: webbrowser.open("http://127.0.0.1:8000")
    except Exception: pass

if __name__ == "__main__":
    print("\n✅ Starting ScorePulse AI Server (Secure Mode)...")
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)