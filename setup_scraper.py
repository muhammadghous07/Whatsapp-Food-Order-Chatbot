from app.utils.scraper import MenuScraper
import json

def test_scraper():
    """Test the scraper"""
    print("🔍 Testing scraper...")
    
    scraper = MenuScraper()
    
    # Test scraping
    menu_items = scraper.scrape_menu()
    
    print(f"✅ Found {len(menu_items)} menu items")
    
    # Display sample items
    print("\n🍽️ Sample Menu Items:")
    for i, item in enumerate(menu_items[:10], 1):
        print(f"{i}. {item['name']} - Rs. {item['price']} ({item['category']})")
    
    # Save to database
    from app.models.database import SessionLocal, MenuItem, Base, engine
    from sqlalchemy.orm import Session
    
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # Clear existing menu items
        db.query(MenuItem).delete()
        db.commit()
        
        # Add new items
        for item_data in menu_items:
            menu_item = MenuItem(
                name=item_data['name'],
                description=item_data.get('description', ''),
                price=item_data['price'],
                category=item_data.get('category', 'Other'),
                is_available=True
            )
            db.add(menu_item)
        
        db.commit()
        print(f"✅ Added {len(menu_items)} items to database")
        
    except Exception as e:
        print(f"❌ Error saving to database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_scraper()