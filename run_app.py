import subprocess
import time
import sys
import os

def run_fastapi():
    """Run FastAPI server"""
    print("🚀 Starting FastAPI Server with Voice Support...")
    try:
        subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"])
    except KeyboardInterrupt:
        print("⏹️ FastAPI Server stopped")

def run_streamlit():
    """Run Streamlit app"""
    print("🎈 Starting Streamlit App with Voice Order...")
    time.sleep(3)  # Wait for FastAPI to start
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--server.port", "8501"])
    except KeyboardInterrupt:
        print("⏹️ Streamlit App stopped")

if __name__ == "__main__":
    print("🍕 FoodExpress Pakistan - Voice Order System")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("app"):
        print("❌ Error: 'app' directory not found. Please run from project root.")
        sys.exit(1)
    
    print("1. FastAPI Backend: http://localhost:8000")
    print("2. Streamlit Frontend: http://localhost:8501") 
    print("3. API Docs: http://localhost:8000/docs")
    print("4. Voice Order: Available in Streamlit")
    print("=" * 50)
    
    try:
        # Run both servers (you'll need to run them in separate terminals)
        print("⚠️  Please run in TWO separate terminals:")
        print("Terminal 1: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        print("Terminal 2: streamlit run streamlit_app.py")
        print("\nOr run them manually as shown above.")
        
        # Option: Run FastAPI (comment out if you want to run manually)
        run_fastapi()
        
    except Exception as e:
        print(f"❌ Error: {e}")