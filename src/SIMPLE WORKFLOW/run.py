import uvicorn
import sys

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 70)
    print(" POST-MORTEM BODY REGISTRY & SEARCH SYSTEM")
    print(" Simple Body Details Intake + Fast Body Search")
    print("=" * 70)
    print(" Web Portal:         http://127.0.0.1:8000")
    print(" API Documentation:  http://127.0.0.1:8000/docs")
    print("=" * 70)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
