import subprocess
import sys
import os
import time

def check_python_version():
    """Check Python version"""
    print("🔍 Checking Python version...")
    version = sys.version_info
    print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return version.major == 3 and version.minor >= 8

def install_requirements():
    """Install requirements"""
    print("📦 Installing requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_fixed.txt"])
        print("   ✅ Requirements installed successfully")
    except Exception as e:
        print(f"   ❌ Error installing requirements: {e}")
        return False
    return True

def setup_database():
    """Setup database"""
    print("🗄️ Setting up database...")
    try:
        subprocess.check_call([sys.executable, "setup_scraper.py"])
        print("   ✅ Database setup completed")
    except Exception as e:
        print(f"   ❌ Error setting up database: {e}")
        return False
    return True

def run_fastapi():
    """Run FastAPI server"""
    print("\n🚀 Starting FastAPI Server...")
    print("   🌐 URL: http://localhost:8000")
    print("   📚 Docs: http://localhost:8000/docs")
    try:
        subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"])
    except KeyboardInterrupt:
        print("⏹️ FastAPI Server stopped")
        return True
    except Exception as e:
        print(f"   ❌ Error running FastAPI: {e}")
        return False

def run_streamlit():
    """Run Streamlit app"""
    print("\n🎈 Starting Streamlit App...")
    print("   🌐 URL: http://localhost:8501")
    time.sleep(3)  # Wait for FastAPI to start
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--server.port", "8501"])
    except KeyboardInterrupt:
        print("⏹️ Streamlit App stopped")
        return True
    except Exception as e:
        print(f"   ❌ Error running Streamlit: {e}")
        return False

def main():
    print("=" * 70)
    print("🍕 FoodExpress Pakistan - Voice Order System - FIXED VERSION")
    print("=" * 70)
    
    # Check if we're in the right directory
    if not os.path.exists("app"):
        print("❌ Error: 'app' directory not found. Please run from project root.")
        return
    
    # Check Python version
    if not check_python_version():
        print("⚠️  Python 3.8 or higher is recommended")
    
    print("\n🔧 Please run the following steps:")
    print("1. Install requirements: pip install -r requirements_fixed.txt")
    print("2. Setup database: python setup_scraper.py")
    print("3. Run FastAPI: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print("4. Run Streamlit: streamlit run streamlit_app.py")
    print("\n⚠️  Run in TWO separate terminals for best results!")
    
    choice = input("\nRun automated setup? (y/n): ").lower()
    
    if choice == 'y':
        # Install requirements
        if not install_requirements():
            return
        
        # Setup database
        if not setup_database():
            return
        
        # Run servers
        print("\n" + "=" * 70)
        print("Starting both servers...")
        print("=" * 70)
        
        # Note: We can't run both in same process easily, so show instructions
        print("\n⚠️  Please run in TWO separate terminals:")
        print("Terminal 1: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        print("Terminal 2: streamlit run streamlit_app.py")
    else:
        print("\n📝 Manual setup instructions:")
        print("1. Open Terminal 1:")
        print("   cd \"C:\\Users\\Muhammad Ghous\\Documents\\WhatsApp Food Order\"")
        print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        print("\n2. Open Terminal 2:")
        print("   cd \"C:\\Users\\Muhammad Ghous\\Documents\\WhatsApp Food Order\"")
        print("   streamlit run streamlit_app.py")
    
    print("\n" + "=" * 70)
    print("✅ Setup instructions completed!")
    print("=" * 70)

if __name__ == "__main__":
    main()