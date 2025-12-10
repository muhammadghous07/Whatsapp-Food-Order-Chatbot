import os
import shutil

def fix_issues():
    """Apply quick fixes"""
    print("🔧 Applying quick fixes...")
    
    # 1. Check and create .env if missing
    if not os.path.exists('.env'):
        print("   📝 Creating .env file...")
        with open('.env', 'w') as f:
            f.write('''DATABASE_URL=sqlite:///./whatsapp_food.db
GREEN_API_ID=7105391740
GREEN_API_TOKEN=d55d909ca87c45af9e5b9781de6f8ae585e63d5cd3a24bb9a1
DEBUG=True
PORT=8000
''')
        print("   ✅ .env file created")
    
    # 2. Check and create data directory
    if not os.path.exists('data'):
        print("   📁 Creating data directory...")
        os.makedirs('data', exist_ok=True)
        print("   ✅ data directory created")
    
    # 3. Check database file
    db_file = 'whatsapp_food.db'
    if os.path.exists(db_file):
        print(f"   ✅ Database file exists: {db_file}")
    else:
        print(f"   📊 Database file will be created on first run")
    
    # 4. Check if app directory exists
    if not os.path.exists('app'):
        print("   ❌ ERROR: 'app' directory not found!")
        print("   💡 Make sure you're running from the correct directory")
        return False
    
    print("\n✅ Quick fixes applied successfully!")
    print("\n📝 Next steps:")
    print("1. Run: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print("2. Open another terminal and run: streamlit run streamlit_app.py")
    print("3. Visit: http://localhost:8501 for the app")
    
    return True

if __name__ == "__main__":
    fix_issues()