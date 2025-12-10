from dotenv import load_dotenv
import os

load_dotenv()

print("🔍 Testing Environment Variables:")
print(f"GREEN_API_ID: {os.getenv('GREEN_API_ID')}")
print(f"GREEN_API_TOKEN: {os.getenv('GREEN_API_TOKEN')}")

if os.getenv('GREEN_API_ID') and os.getenv('GREEN_API_TOKEN'):
    print("✅ Environment variables loaded successfully!")
else:
    print("❌ Environment variables NOT loaded!")