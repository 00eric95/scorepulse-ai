import os
import sys
import webbrowser
import threading
import time

# This script forces Python to look in the 'src' folder,
# starts the server, and automatically opens your browser.

def open_browser():
    """Waits for the server to start, then opens the browser."""
    time.sleep(4) # Give the server a moment to start
    print("[INFO] Opening web browser...")
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    print("--- ATTEMPTING TO START SCOREPULSE AI ---")
    
    # 1. Get the absolute path of the directory containing this script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Check if 'src' exists here
    src_path = os.path.join(BASE_DIR, "src")
    
    if os.path.exists(src_path):
        print(f"[OK] Found 'src' folder at: {src_path}")
        
        # 3. Add 'src' to PYTHONPATH Environment Variable
        # CRITICAL FIX: This ensures the Uvicorn reloader (subprocess) also sees the path
        current_pythonpath = os.environ.get("PYTHONPATH", "")
        os.environ["PYTHONPATH"] = src_path + os.pathsep + current_pythonpath
        
        # Also add to current process just in case
        sys.path.append(BASE_DIR)
        sys.path.append(src_path)
        
        # 4. Try to import uvicorn
        try:
            import uvicorn
        except ImportError:
            print("[ERROR] uvicorn is not installed.")
            print("[INFO] Run this command to install required packages:")
            print("  C:/Users/LENOVO/anaconda3/python.exe -m pip install uvicorn fastapi jinja2")
            sys.exit(1)
        
        # 5. Start the server
        print("---------------------------------------")
        print("[OK] Server is running! Access it here:")
        print("[URL] http://127.0.0.1:8000")
        print("---------------------------------------")
        
        # 6. Schedule the browser to open (New Feature)
        threading.Thread(target=open_browser, daemon=True).start()
        
        try:
            # We use "main:app" because PYTHONPATH now includes 'src'
            # This makes imports inside main.py (like 'from core...') work naturally
            uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
        except KeyboardInterrupt:
            print("\n[STOP] Server stopped by user.")
        except Exception as e:
            print(f"[ERROR] CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            input("Press Enter to exit...")
            
    else:
        # Fallback: Maybe the user put this script INSIDE src by mistake?
        if os.path.exists(os.path.join(BASE_DIR, "main.py")):
            print("[WARN] You seem to be running this from inside the 'src' folder.")
            print("[INFO] Starting Server...")
            try:
                import uvicorn
                uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
            except ImportError:
                print("[ERROR] uvicorn is not installed.")
                print("[INFO] Run this command to install required packages:")
                print("  C:/Users/LENOVO/anaconda3/python.exe -m pip install uvicorn fastapi jinja2")
                sys.exit(1)
        else:
            print("[ERROR] Could not find the 'src' folder.")
            print(f"[INFO] I am currently looking in: {BASE_DIR}")
            print("[INFO] Please move this file to the main 'SCORE_pulseAI' folder.")
            input("Press Enter to exit...")