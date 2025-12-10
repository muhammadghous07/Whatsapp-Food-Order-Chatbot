from dotenv import load_dotenv
load_dotenv()  

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, engine, Base, MenuItem, Branch, User, Order
from app.routers import webhook, admin, voice
from app.utils.scraper import MenuScraper
from app.services.whatsapp_service import WhatsAppService
from app.services.voice_service import voice_service
import uvicorn
import os
import traceback
from datetime import datetime
from sqlalchemy import inspect

# Debug: Check if environment variables are loading
print("🔍 Environment Variables Check:")
print(f"   GREEN_API_ID: {os.getenv('GREEN_API_ID', 'NOT FOUND')}")
print(f"   GREEN_API_TOKEN: {os.getenv('GREEN_API_TOKEN', 'NOT FOUND')[:10]}...")  # Show first 10 chars only
print(f"   DATABASE_URL: {os.getenv('DATABASE_URL', 'sqlite:///./foodexpress.db')}")

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WhatsApp Food Order Chatbot - Pakistan (GREEN-API + Voice)",
    description="AI-powered food ordering system via WhatsApp with GREEN-API Integration & Voice Recognition",
    version="6.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include routers
app.include_router(webhook.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1/admin")
app.include_router(voice.router, prefix="/api/v1/voice")

def check_voice_service_status():
    """Check voice service status safely"""
    try:
        if hasattr(voice_service, 'asr_pipeline') and voice_service.asr_pipeline:
            return "HuggingFace Wav2Vec2", True
        elif hasattr(voice_service, 'whisper_model') and voice_service.whisper_model:
            return "Whisper", True
        else:
            return "Google Speech Recognition", True
    except Exception as e:
        print(f"❌ Voice service check failed: {e}")
        return "Not Available", False

def check_whatsapp_service_status():
    """Check WhatsApp service status safely"""
    try:
        whatsapp_service = WhatsAppService()
        return whatsapp_service.check_whatsapp_health()
    except Exception as e:
        print(f"❌ WhatsApp service check failed: {e}")
        return {
            "status": "error",
            "green_api": False,
            "error": str(e)
        }

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup - COMPLETELY FIXED VERSION"""
    print("=" * 70)
    print("🚀 Starting WhatsApp Food Order Chatbot - Voice Enhanced Edition...")
    print("=" * 70)
    
    try:
        # Initialize menu data with better error handling
        scraper = MenuScraper()
        menu_data = []
        
        print("🌐 Attempting to initialize menu...")
        try:
            # Try scraping first
            print("   Step 1: Attempting to scrape menu from website...")
            scraped_data = scraper.scrape_menu()
            if scraped_data and len(scraped_data) > 0:
                menu_data = scraped_data
                print(f"   ✅ Successfully scraped {len(menu_data)} menu items")
            else:
                raise Exception("No data returned from scraper")
        except Exception as e:
            print(f"   ⚠️ Scraping failed: {str(e)}")
            print("   🔧 Falling back to built-in Pakistani menu...")
            try:
                menu_data = scraper.create_pakistani_menu()
                print(f"   ✅ Created {len(menu_data)} Pakistani menu items")
            except Exception as inner_e:
                print(f"   ❌ Built-in menu failed: {inner_e}")
                print("   🚨 Using emergency fallback menu...")
                menu_data = scraper.create_emergency_menu()
                print(f"   ✅ Created {len(menu_data)} emergency menu items")
        
        print("✅ Menu initialization completed")
        
        # Initialize WhatsApp Service with retry logic
        print("\n📱 Initializing WhatsApp Service...")
        whatsapp_health = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                whatsapp_service = WhatsAppService()
                whatsapp_health = whatsapp_service.check_whatsapp_health()
                
                if whatsapp_health.get('green_api'):
                    if whatsapp_health.get('status') == 'connected':
                        print("   ✅ GREEN-API Connected Successfully!")
                        print(f"   📞 WhatsApp State: {whatsapp_health.get('whatsapp_state', 'Unknown')}")
                        break
                    else:
                        print(f"   🔶 GREEN-API: Attempt {attempt + 1} - Not connected")
                else:
                    print(f"   🔶 Attempt {attempt + 1} - Running in DEMO Mode")
                    break
                    
            except Exception as e:
                print(f"   ⚠️ Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    print("   🔄 Retrying in 2 seconds...")
                    import time
                    time.sleep(2)
                else:
                    print("   ❌ Max retries reached. WhatsApp service may not be available.")
                    whatsapp_health = {"status": "demo_mode", "green_api": False}
        
        # Voice service status - FIXED: Using safe check
        print("\n🎤 Initializing Voice Service...")
        voice_model, voice_loaded = check_voice_service_status()
        if voice_loaded:
            print(f"   ✅ {voice_model}: Active")
        else:
            print(f"   🔶 {voice_model}: Active (Fallback)")
        
        try:
            languages = voice_service.supported_languages()
            print(f"   🌍 Supported Languages: {', '.join(languages)}")
        except:
            print("   🌍 Supported Languages: English, Urdu, Hindi")
        
        # Verify database data with better error handling - COMPLETELY FIXED
        print("\n📊 Verifying Database...")
        db = None
        try:
            db = SessionLocal()
            
            # Check if tables exist using SQLAlchemy inspect
            inspector = inspect(db.bind)
            table_names = inspector.get_table_names()
            
            if 'menu_items' not in table_names:
                print("   ⚠️ Tables not created yet. Creating tables...")
                Base.metadata.create_all(bind=engine)
                print("   ✅ Tables created successfully")
            
            # Now tables should exist, check counts - REMOVED DUPLICATE IMPORTS
            menu_count = db.query(MenuItem).count()
            branch_count = db.query(Branch).count()
            user_count = db.query(User).count()
            order_count = db.query(Order).count()
            
            # If no menu items, insert the menu data - FIXED: Use MenuItem already imported at top
            if menu_count == 0:
                print("   ℹ️ No menu items found. Inserting default menu...")
                
                for item_data in menu_data:
                    menu_item = MenuItem(
                        name=item_data.get('name', 'Unknown Item'),
                        price=item_data.get('price', 0),
                        category=item_data.get('category', 'Other'),
                        description=item_data.get('description', ''),
                        is_available=True
                    )
                    db.add(menu_item)
                
                try:
                    db.commit()
                    # Re-query to get updated count
                    menu_count = db.query(MenuItem).count()
                    print(f"   ✅ Inserted {menu_count} menu items")
                except Exception as commit_error:
                    print(f"   ❌ Failed to commit menu items: {commit_error}")
                    db.rollback()
            
            print("   ✅ Database Verified:")
            print(f"      • Menu Items: {menu_count}")
            print(f"      • Branches: {branch_count}")
            print(f"      • Users: {user_count}")
            print(f"      • Orders: {order_count}")
            print(f"      • Currency: Pakistani Rupees (Rs.)")
            print(f"      • WhatsApp: {'GREEN-API' if whatsapp_health.get('green_api', False) else 'DEMO'}")
            print(f"      • Voice: {voice_model}")
            
            # Show sample menu items
            if menu_count > 0:
                sample_items = db.query(MenuItem).limit(5).all()
                if sample_items:
                    print(f"      🍽️  Sample Menu:")
                    for item in sample_items:
                        print(f"        • {item.name} - Rs. {item.price:,.0f}")
            else:
                print("      ⚠️ No menu items in database")
            
        except Exception as db_error:
            print(f"   ❌ Database error: {str(db_error)}")
            print("   ⚠️ Database operations may be limited")
            import traceback
            traceback.print_exc()
        finally:
            if db:
                db.close()
        
        print("\n" + "=" * 70)
        print("✅ Application startup completed successfully!")
        print("=" * 70)
        print("\n🌐 Server running at: http://localhost:8000")
        print("📚 API Documentation: http://localhost:8000/docs")
        print("💬 Demo Chat: POST /api/v1/demo/chat")
        print("🎤 Voice Test: POST /api/v1/voice/transcribe")
        print("📱 WhatsApp Test: POST /api/v1/whatsapp/send-test")
        print("❤️  Health Check: GET /health")
        print("📊 System Health: GET /system-health")
        print("🎵 Voice Support: GET /api/v1/voice/voice-supported")
        print("💻 Streamlit Demo: http://localhost:8501")
        print("\n🔧 Troubleshooting:")
        print("   • If WhatsApp not working: Check GREEN-API credentials")
        print("   • If voice not working: Check internet connection for model download")
        print("   • If database issues: Check DATABASE_URL in .env file")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Fatal error during startup: {str(e)}")
        print("Stack trace:")
        traceback.print_exc()
        print("\n⚠️ Application started with errors. Some features may not work.")
        print("🔧 Please check the error messages above and fix the issues.")

@app.get("/")
async def root():
    """Root endpoint with basic API information"""
    try:
        whatsapp_health = check_whatsapp_service_status()
        voice_model, voice_loaded = check_voice_service_status()
        
        return {
            "message": "WhatsApp Food Order Chatbot API - GREEN-API & Voice Powered", 
            "status": "running",
            "database": "SQLite",
            "currency": "Pakistani Rupees (Rs.)",
            "whatsapp_service": "GREEN-API" if whatsapp_health.get('green_api') else "DEMO",
            "whatsapp_status": whatsapp_health.get('status', 'unknown'),
            "voice_service": voice_model,
            "voice_status": "active" if voice_loaded else "limited",
            "languages": "English, Hindi, Roman Urdu, Urdu",
            "version": "6.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "endpoints": {
                "docs": "/docs",
                "health": "/health", 
                "system_health": "/system-health",
                "whatsapp_health": "/api/v1/whatsapp/health",
                "voice_support": "/api/v1/voice/voice-supported",
                "send_test_message": "/api/v1/whatsapp/send-test (POST)",
                "demo_chat": "/api/v1/demo/chat (POST)",
                "voice_transcribe": "/api/v1/voice/transcribe (POST)",
                "menu": "/menu",
                "stats": "/stats"
            }
        }
    except Exception as e:
        return {
            "message": "API Service",
            "status": "running",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/health")
async def health_check():
    """Simple health check endpoint for basic connectivity"""
    try:
        # Test database connection with proper error handling
        db = None
        db_status = "disconnected"
        db_error_msg = None
        
        try:
            db = SessionLocal()
            # Simple query to test connection
            db.execute("SELECT 1")
            db_status = "connected"
        except Exception as db_error:
            db_status = "disconnected"
            db_error_msg = str(db_error)
        finally:
            if db:
                db.close()
        
        # Check WhatsApp service
        whatsapp_health = check_whatsapp_service_status()
        
        # Check voice service
        voice_model, voice_loaded = check_voice_service_status()
        
        status = "healthy" if db_status == "connected" else "degraded"
        
        response = {
            "status": status,
            "service": "whatsapp-food-order",
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_status,
            "whatsapp": whatsapp_health.get('status', 'unknown'),
            "voice": voice_model,
            "version": "6.0.0"
        }
        
        if db_error_msg:
            response["warning"] = f"Database: {db_error_msg}"
            
        return response
                
    except Exception as e:
        # Don't raise HTTPException, return a JSON response instead
        return {
            "status": "unhealthy",
            "service": "whatsapp-food-order",
            "timestamp": datetime.utcnow().isoformat(), 
            "error": str(e)
        }

@app.get("/system-health")
async def system_health_check():
    """Comprehensive system health check"""
    try:
        # Test database
        db = None
        db_status = "unknown"
        menu_count = 0
        branch_count = 0
        user_count = 0
        
        try:
            db = SessionLocal()
            db.execute("SELECT 1")
            db_status = "connected"
            menu_count = db.query(MenuItem).count()
            branch_count = db.query(Branch).count()
            user_count = db.query(User).count()
        except Exception as e:
            db_status = f"error: {str(e)}"
        finally:
            if db:
                db.close()
        
        # Check WhatsApp service
        whatsapp_health = check_whatsapp_service_status()
        
        # Check voice service
        voice_model, voice_loaded = check_voice_service_status()
        voice_health = {
            "model": voice_model,
            "loaded": voice_loaded,
            "status": "active" if voice_loaded else "limited"
        }
        
        # Determine overall status
        overall_status = "healthy"
        if db_status != "connected":
            overall_status = "degraded"
        if not voice_loaded:
            overall_status = "limited"
        if whatsapp_health.get('status') != 'connected':
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": {
                    "status": db_status,
                    "menu_items": menu_count,
                    "branches": branch_count,
                    "users": user_count
                },
                "whatsapp_service": whatsapp_health,
                "voice_service": voice_health,
                "api": "running"
            },
            "environment": {
                "green_api_enabled": whatsapp_health.get('green_api', False),
                "debug_mode": os.getenv('DEBUG', 'False').lower() == 'true',
                "voice_enabled": True,
                "python_version": os.getenv('PYTHON_VERSION', 'Unknown')
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@app.get("/test-db")
async def test_database():
    """Test database connection and data"""
    try:
        db = SessionLocal()
        menu_count = db.query(MenuItem).count()
        branch_count = db.query(Branch).count()
        user_count = db.query(User).count()
        order_count = db.query(Order).count()
        
        # Get all menu items
        menu_items = db.query(MenuItem).all()
        menu_data = [
            {
                "id": item.id,
                "name": item.name,
                "price": f"Rs. {item.price:,.0f}",
                "category": item.category,
                "available": item.is_available
            }
            for item in menu_items
        ]
        
        db.close()
        
        voice_model, voice_loaded = check_voice_service_status()
        
        return {
            "database": "SQLite",
            "status": "connected",
            "currency": "Pakistani Rupees",
            "voice_support": True,
            "voice_model": voice_model,
            "voice_loaded": voice_loaded,
            "statistics": {
                "menu_items": menu_count,
                "branches": branch_count,
                "users": user_count,
                "orders": order_count
            },
            "menu": menu_data[:10],  # Show first 10 items only
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "error": str(e), 
            "status": "database_error",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/menu")
async def get_full_menu():
    """Get complete menu with better error handling"""
    try:
        db = SessionLocal()
        menu_items = db.query(MenuItem).filter(MenuItem.is_available == True).all()
        
        # Group by category
        menu_by_category = {}
        for item in menu_items:
            category = item.category or "Other"
            if category not in menu_by_category:
                menu_by_category[category] = []
            menu_by_category[category].append({
                "id": item.id,
                "name": item.name,
                "price": item.price,
                "formatted_price": f"Rs. {item.price:,.0f}",
                "description": item.description or "",
                "available": item.is_available
            })
        
        db.close()
        
        voice_model, voice_loaded = check_voice_service_status()
        
        return {
            "currency": "Pakistani Rupees",
            "total_items": len(menu_items),
            "voice_support": True,
            "voice_model": voice_model,
            "menu_by_category": menu_by_category,
            "categories": list(menu_by_category.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to fetch menu",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/stats")
async def get_system_stats():
    """Get system statistics with error handling"""
    try:
        db = SessionLocal()
        
        menu_count = db.query(MenuItem).count()
        branch_count = db.query(Branch).count()
        user_count = db.query(User).count()
        order_count = db.query(Order).count()
        
        # Get available menu items
        available_menu_count = db.query(MenuItem).filter(MenuItem.is_available == True).count()
        
        # Get active branches
        active_branches_count = db.query(Branch).filter(Branch.is_active == True).count()
        
        # Get today's date
        today = datetime.utcnow().date()
        
        # Get today's orders
        today_orders_count = db.query(Order).filter(
            Order.created_at >= datetime(today.year, today.month, today.day)
        ).count()
        
        # Get total revenue
        total_revenue = db.query(db.func.sum(Order.total_amount)).scalar() or 0
        
        db.close()
        
        voice_model, voice_loaded = check_voice_service_status()
        whatsapp_health = check_whatsapp_service_status()
        
        return {
            "statistics": {
                "menu": {
                    "total": menu_count,
                    "available": available_menu_count,
                    "unavailable": menu_count - available_menu_count
                },
                "branches": {
                    "total": branch_count,
                    "active": active_branches_count,
                    "inactive": branch_count - active_branches_count
                },
                "users": {
                    "total": user_count
                },
                "orders": {
                    "total": order_count,
                    "today": today_orders_count,
                    "total_revenue": f"Rs. {total_revenue:,.0f}"
                }
            },
            "services": {
                "voice": {
                    "model": voice_model,
                    "loaded": voice_loaded
                },
                "whatsapp": {
                    "service": "GREEN-API" if whatsapp_health.get('green_api') else "DEMO",
                    "status": whatsapp_health.get('status', 'unknown')
                }
            },
            "currency": "Pakistani Rupees",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to fetch statistics",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/voice-demo")
async def voice_demo_info():
    """Voice demo information endpoint"""
    try:
        voice_model, voice_loaded = check_voice_service_status()
        
        # Get supported languages safely
        try:
            languages = voice_service.supported_languages()
        except:
            languages = ["English", "Urdu", "Hindi"]
        
        return {
            "voice_service": "Active",
            "voice_model": voice_model,
            "features": [
                "Free HuggingFace Wav2Vec2 Voice Recognition",
                "Google Speech Recognition Fallback", 
                "Multi-language Support",
                "Streamlit UI Integration",
                "Real-time Audio Processing"
            ],
            "supported_formats": ["WAV", "MP3", "M4A"],
            "usage": {
                "streamlit": "Use Voice Order tab in Streamlit UI",
                "api": "POST /api/v1/voice/transcribe with audio file",
                "whatsapp": "Voice messages automatically processed"
            },
            "languages": languages,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "voice_service": "Limited",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/api-status")
async def api_status():
    """Get API status and all available endpoints"""
    try:
        # Get all routes
        routes = []
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                routes.append({
                    "path": route.path,
                    "methods": list(route.methods) if route.methods else [],
                    "name": route.name if hasattr(route, "name") else "unnamed"
                })
        
        # System health
        system_health = await system_health_check()
        
        return {
            "api_name": "WhatsApp Food Order Chatbot API",
            "version": "6.0.0",
            "status": system_health.get("status", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "total_endpoints": len(routes),
            "endpoints": routes,
            "system": system_health
        }
    except Exception as e:
        return {
            "api_name": "WhatsApp Food Order Chatbot API",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    print("🚀 Starting server directly (not recommended for production)...")
    print("📝 Use: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print("💡 Tip: Run with --reload flag for development")
    
    # Parse command line arguments if any
    import sys
    host = "0.0.0.0"
    port = 8000
    reload = False
    
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--host" and i + 1 < len(args):
            host = args[i + 1]
        elif arg == "--port" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except:
                pass
        elif arg == "--reload":
            reload = True
    
    print(f"🌐 Starting on: http://{host}:{port}")
    print(f"🔄 Reload: {'Enabled' if reload else 'Disabled'}")
    
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)