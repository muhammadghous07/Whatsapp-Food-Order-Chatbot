import requests
import json

def test_api():
    """Simple test to check if API is working"""
    print("🧪 Testing FoodExpress API...")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8000/health")
        print(f"✅ Health Check: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Test menu endpoint
        response = requests.get("http://localhost:8000/menu")
        print(f"✅ Menu Check: {response.status_code}")
        menu_data = response.json()
        print(f"   Menu Items: {len(menu_data.get('menu', []))}")
        
        # Test conversations endpoint
        response = requests.get("http://localhost:8000/api/v1/conversations/923002514961")
        print(f"✅ Conversations Check: {response.status_code}")
        conv_data = response.json()
        print(f"   Conversations: {len(conv_data.get('conversations', []))}")
        
        print("\n🎉 All tests passed! Your API is working correctly.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure your FastAPI server is running on http://localhost:8000")

if __name__ == "__main__":
    test_api()