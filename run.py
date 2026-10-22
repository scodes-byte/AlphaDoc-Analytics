import uvicorn
import os
import webbrowser
import threading
import time
from dotenv import load_dotenv

load_dotenv()
PORT = int(os.getenv("PORT", "8000"))

def open_browser():
    """
    Waits briefly for the uvicorn server to bind and load, 
    then opens the dashboard link in the default browser.
    """
    time.sleep(1.5)
    print("\n[System] Opening AlphaDoc-Analytics interface in your default browser...\n")
    webbrowser.open(f"http://127.0.0.1:{PORT}")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  ALPHADOC-ANALYTICS: GenAI & Data Science Multi-Agent Document Platform")
    print(f"  Running locally on: http://127.0.0.1:{PORT}")
    print("="*70 + "\n")
    
    # Spawn browser opener on a separate daemon thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run("backend.app:app", host="127.0.0.1", port=PORT, reload=True)
