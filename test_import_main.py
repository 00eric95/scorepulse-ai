import sys
sys.path.insert(0, 'src')
try:
    import main
    print('OK - imported main')
except Exception as e:
    print('IMPORT FAILED:', type(e).__name__, e)
    import traceback
    traceback.print_exc()
