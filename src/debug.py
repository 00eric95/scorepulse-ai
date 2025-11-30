import os
import sys
import traceback

print("--- DEBUGGING STARTED ---")
print(f"1. Current Folder: {os.getcwd()}")

print("\n2. Files in this folder:")
files = os.listdir()
if "main.py" in files:
    print("   [OK] main.py found.")
elif "main.py.py" in files:
    print("   [ERROR] Found 'main.py.py'. Please rename it to 'main.py'!")
else:
    print("   [ERROR] main.py NOT found. Here is what exists:")
    for f in files:
        print(f"   - {f}")

print("\n3. Attempting to import 'main'...")
try:
    # This simulates what Uvicorn tries to do
    import main
    print("\n[SUCCESS] 'main.py' imported successfully! The code is fine.")
    print("If you see this, try running: python -m uvicorn main:app --reload")
except Exception:
    print("\n[CRITICAL FAILURE] main.py exists but CRASHED during loading.")
    print("Here is the real error that Uvicorn was hiding:\n")
    traceback.print_exc()