import uvicorn
import os
import sys

if __name__ == "__main__":
    # Add backend to sys.path to allow correct imports of pipeline modules
    root_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(root_dir)
    sys.path.append(os.path.join(root_dir, "backend"))
    
    print("\n" + "="*70)
    print("  ALPHADOC-ANALYTICS: GenAI & Data Science Multi-Agent Document Platform")
    print("  Running locally on: http://127.0.0.1:8000")
    print("="*70 + "\n")
    
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
