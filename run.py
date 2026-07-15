import uvicorn
import os
import sys
import webbrowser
import threading
import time

def open_browser():
    """
    Waits briefly for the uvicorn server to bind and load, 
    then opens the dashboard link in the default browser.
    """
    time.sleep(1.5)
    print("\n[System] Opening AlphaDoc-Analytics interface in your default browser...\n")
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    # Add backend to sys.path to allow correct imports of pipeline modules
    root_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(root_dir)
    sys.path.append(os.path.join(root_dir, "backend"))
    
    print("\n" + "="*70)
    print("  ALPHADOC-ANALYTICS: GenAI & Data Science Multi-Agent Document Platform")
    print("  Running locally on: http://127.0.0.1:8000")
    print("="*70 + "\n")
    
    # Spawn browser opener on a separate daemon thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
