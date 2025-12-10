from app.models.database import SessionLocal, Base, engine, MenuItem, Branch, User, Order, OrderItem, Conversation
import json
import os
import sys

# Add the parent directory to the path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def setup_database():
    """Initialize SQLite Database with sample data"""
    print("🗄️ Setting up SQLite Database...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Clear existing data in correct order (due to foreign key constraints)
        print("🧹 Clearing existing data...")
        db.query(Conversation).delete()
        db.query(OrderItem).delete()
        db.query(Order).delete()
        db.query(MenuItem).delete()
        db.query(Branch).delete()
        db.query(User).delete()
        db.commit()
        
        # Load menu items
        print("🍽️ Loading menu items...")
        
        # Try to use the scraper, but have a fallback
        try:
            from app.utils.scraper import MenuScraper
            scraper = MenuScraper()
            menu_data = scraper.create_pakistani_menu()  # Use the Pakistani menu directly
            print(f"✅ Using {len(menu_data)} menu items from scraper")
        except ImportError as e:
            print(f"⚠️ Could not import MenuScraper: {e}")
            print("🔧 Using built-in menu items...")
            menu_data = get_default_menu()
        
        # Add menu items
        print(f"➕ Adding {len(menu_data)} menu items...")
        for item_data in menu_data:
            menu_item = MenuItem(
                name=item_data['name'],
                description=item_data.get('description', ''),
                price=item_data['price'],
                category=item_data.get('category', 'Other'),
                is_available=item_data.get('is_available', True)
            )
            db.add(menu_item)
        
        # Add branches
        print("➕ Adding branches...")
        branches = [
            Branch(
                name="Coffee Wagera Karachi",
                address="Tariq Road, Karachi, Pakistan",
                latitude=24.8607,
                longitude=67.0011,
                phone_number="+923001234567",
                is_active=True
            ),
            Branch(
                name="Coffee Wagera Lahore", 
                address="Liberty Market, Lahore, Pakistan",
                latitude=31.5204,
                longitude=74.3587,
                phone_number="+923001234568",
                is_active=True
            ),
            Branch(
                name="Coffee Wagera Islamabad",
                address="F-7 Markaz, Islamabad, Pakistan", 
                latitude=33.738045,
                longitude=73.084488,
                phone_number="+923001234569",
                is_active=True
            ),
            Branch(
                name="Coffee Wagera Rawalpindi",
                address="Saddar, Rawalpindi, Pakistan",
                latitude=33.5651,
                longitude=73.0169,
                phone_number="+923001234570",
                is_active=True
            ),
            Branch(
                name="Coffee Wagera Faisalabad",
                address="Kohinoor City, Faisalabad, Pakistan",
                latitude=31.4504,
                longitude=73.1350,
                phone_number="+923001234571",
                is_active=True
            )
        ]
        
        for branch in branches:
            db.add(branch)
        
        # Add sample user
        print("➕ Adding sample user...")
        user = User(
            phone_number="923002514961",
            name="Muhammad Ghous"
        )
        db.add(user)
        
        # Add sample conversations
        print("➕ Adding sample conversations...")
        conversations = [
            Conversation(
                user_id=1,
                phone_number="923002514961",
                message_type="user",
                message_text="Hello, I want to order coffee"
            ),
            Conversation(
                user_id=1,
                phone_number="923002514961",
                message_type="bot",
                message_text="Hello! Welcome to Coffee Wagera. What would you like to order?"
            ),
            Conversation(
                user_id=1,
                phone_number="923002514961",
                message_type="user",
                message_text="2 cappuccino and 1 cookie"
            ),
            Conversation(
                user_id=1,
                phone_number="923002514961",
                message_type="bot",
                message_text="Great! Please share your delivery location."
            )
        ]
        
        for conv in conversations:
            db.add(conv)
        
        db.commit()
        
        print("✅ Database setup completed!")
        
        # Print summary
        menu_count = db.query(MenuItem).count()
        branch_count = db.query(Branch).count()
        user_count = db.query(User).count()
        conversation_count = db.query(Conversation).count()
        
        print(f"📊 Database Summary:")
        print(f"   • Menu Items: {menu_count}")
        print(f"   • Branches: {branch_count}")
        print(f"   • Users: {user_count}")
        print(f"   • Conversations: {conversation_count}")
        
        # Show sample menu items
        print("\n🍽️ Sample Menu Items:")
        sample_items = db.query(MenuItem).limit(10).all()  # Show more items
        for item in sample_items:
            print(f"   • {item.name} - Rs. {item.price:,.0f} ({item.category})")
        
        print("\n📍 Sample Branches:")
        sample_branches = db.query(Branch).limit(3).all()
        for branch in sample_branches:
            print(f"   • {branch.name} - {branch.address}")
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def get_default_menu():
    """Get default menu items if scraper fails - UPDATED WITH PAKISTANI ITEMS"""
    return [
        {
            "name": "Espresso",
            "price": 250.0,
            "category": "Coffee",
            "description": "Strong black coffee",
            "is_available": True
        },
        {
            "name": "Cappuccino",
            "price": 350.0,
            "category": "Coffee",
            "description": "Coffee with steamed milk",
            "is_available": True
        },
        {
            "name": "Latte",
            "price": 400.0,
            "category": "Coffee",
            "description": "Coffee with lots of milk",
            "is_available": True
        },
        {
            "name": "Americano",
            "price": 300.0,
            "category": "Coffee",
            "description": "Espresso with hot water",
            "is_available": True
        },
        {
            "name": "Mocha",
            "price": 450.0,
            "category": "Coffee",
            "description": "Coffee with chocolate",
            "is_available": True
        },
        {
            "name": "Hot Chocolate",
            "price": 400.0,
            "category": "Beverages",
            "description": "Rich chocolate drink",
            "is_available": True
        },
        {
            "name": "Chai Karak",
            "price": 200.0,
            "category": "Tea",
            "description": "Strong Pakistani tea",
            "is_available": True
        },
        {
            "name": "Green Tea",
            "price": 180.0,
            "category": "Tea",
            "description": "Healthy green tea",
            "is_available": True
        },
        {
            "name": "Cookie",
            "price": 150.0,
            "category": "Pastries",
            "description": "Fresh baked cookie",
            "is_available": True
        },
        {
            "name": "Brownie",
            "price": 250.0,
            "category": "Pastries",
            "description": "Chocolate brownie",
            "is_available": True
        },
        {
            "name": "Croissant",
            "price": 200.0,
            "category": "Pastries",
            "description": "Buttery French croissant",
            "is_available": True
        },
        {
            "name": "Sandwich",
            "price": 450.0,
            "category": "Food",
            "description": "Grilled sandwich",
            "is_available": True
        },
        {
            "name": "Club Sandwich",
            "price": 550.0,
            "category": "Food",
            "description": "Triple decker sandwich",
            "is_available": True
        },
        {
            "name": "French Fries",
            "price": 250.0,
            "category": "Snacks",
            "description": "Crispy golden fries",
            "is_available": True
        },
        {
            "name": "Nachos",
            "price": 400.0,
            "category": "Snacks",
            "description": "Cheesy nachos with salsa",
            "is_available": True
        },
        {
            "name": "Cheese Cake",
            "price": 550.0,
            "category": "Desserts",
            "description": "Creamy cheese cake",
            "is_available": True
        },
        {
            "name": "Chocolate Lava Cake",
            "price": 450.0,
            "category": "Desserts",
            "description": "Warm chocolate cake with molten center",
            "is_available": True
        },
        {
            "name": "Fresh Juice",
            "price": 300.0,
            "category": "Beverages",
            "description": "Seasonal fresh juice",
            "is_available": True
        },
        {
            "name": "Smoothie",
            "price": 400.0,
            "category": "Beverages",
            "description": "Fruit smoothie",
            "is_available": True
        },
        # NEW PAKISTANI ITEMS ADDED HERE
        {
            "name": "Zinger Burger",
            "price": 550.0,
            "category": "Fast Food",
            "description": "Crispy chicken burger with special sauce",
            "is_available": True
        },
        {
            "name": "Chicken Biryani", 
            "price": 450.0,
            "category": "Main Course",
            "description": "Traditional Pakistani biryani",
            "is_available": True
        },
        {
            "name": "Chicken Karahi",
            "price": 650.0,
            "category": "Main Course",
            "description": "Spicy chicken curry",
            "is_available": True
        },
        {
            "name": "Beef Seekh Kabab",
            "price": 500.0,
            "category": "BBQ",
            "description": "Minced beef kababs",
            "is_available": True
        },
        {
            "name": "Chicken Tikka",
            "price": 600.0,
            "category": "BBQ",
            "description": "Grilled chicken pieces",
            "is_available": True
        },
        {
            "name": "Gulab Jamun",
            "price": 200.0,
            "category": "Desserts",
            "description": "Sweet milk balls in syrup",
            "is_available": True
        },
        {
            "name": "Falooda",
            "price": 350.0,
            "category": "Desserts",
            "description": "Traditional Pakistani dessert drink",
            "is_available": True
        },
        {
            "name": "Samosa",
            "price": 100.0,
            "category": "Snacks",
            "description": "Fried pastry with potato filling",
            "is_available": True
        },
        {
            "name": "Pakora",
            "price": 250.0,
            "category": "Snacks",
            "description": "Vegetable fritters",
            "is_available": True
        },
        {
            "name": "Nihari",
            "price": 500.0,
            "category": "Main Course",
            "description": "Slow-cooked beef stew",
            "is_available": True
        },
        {
            "name": "Haleem",
            "price": 400.0,
            "category": "Main Course",
            "description": "Wheat and meat porridge",
            "is_available": True
        }
    ]

if __name__ == "__main__":
    setup_database()