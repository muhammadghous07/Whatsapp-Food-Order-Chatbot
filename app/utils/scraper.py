import requests
from bs4 import BeautifulSoup
import json
import os
import re
import logging
from urllib.parse import urljoin
import time

logger = logging.getLogger(__name__)

class MenuScraper:
    def __init__(self):
        self.base_url = "https://order.coffeewagera.com/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
    
    def scrape_menu(self):
        """Scrape menu from Coffee Wagera website"""
        try:
            logger.info(f"🔍 Scraping menu from {self.base_url}...")
            
            # First, try to get the main page
            response = self.session.get(self.base_url, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ Main page returned status {response.status_code}. Trying menu-specific URLs...")
                return self.try_menu_urls()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for menu links
            menu_links = []
            for link in soup.find_all('a', href=True):
                href = link['href'].lower()
                text = link.get_text().lower()
                if any(keyword in href or keyword in text for keyword in ['menu', 'order', 'food', 'drink', 'coffee', 'burger']):
                    menu_links.append(urljoin(self.base_url, link['href']))
            
            # Try all menu links
            menu_items = []
            for menu_url in set(menu_links)[:3]:  # Try first 3 unique links
                try:
                    items = self.scrape_menu_page(menu_url)
                    if items:
                        menu_items.extend(items)
                        logger.info(f"✅ Found {len(items)} items from {menu_url}")
                except Exception as e:
                    logger.debug(f"⚠️ Error scraping {menu_url}: {e}")
                    continue
            
            if menu_items:
                logger.info(f"✅ Total {len(menu_items)} items scraped")
                self._save_menu(menu_items)
                return menu_items
            else:
                logger.warning("⚠️ No menu items found via links. Trying to extract from main page...")
                return self.extract_from_main_page(soup)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error: {e}")
            return self.create_pakistani_menu()
        except Exception as e:
            logger.error(f"❌ Error scraping menu: {e}")
            return self.create_pakistani_menu()
    
    def try_menu_urls(self):
        """Try common menu URLs"""
        common_menu_urls = [
            f"{self.base_url}menu",
            f"{self.base_url}order",
            f"{self.base_url}food",
            f"{self.base_url}drinks",
            f"{self.base_url}products"
        ]
        
        menu_items = []
        for url in common_menu_urls:
            try:
                items = self.scrape_menu_page(url)
                if items:
                    menu_items.extend(items)
                    logger.info(f"✅ Found {len(items)} items from {url}")
                    break
            except Exception as e:
                logger.debug(f"⚠️ Error scraping {url}: {e}")
                continue
        
        if menu_items:
            self._save_menu(menu_items)
            return menu_items
        else:
            return self.create_pakistani_menu()
    
    def scrape_menu_page(self, url):
        """Scrape menu from a specific page"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for product items - common patterns
            menu_items = []
            item_id = 1
            
            # Pattern 1: Look for product cards (common in e-commerce)
            product_selectors = [
                'div.product', 'div.item', 'div.card', 'div.menu-item',
                'li.product', 'li.item', 'li.menu-item',
                'article.product', 'article.item',
                'div[class*="product"]', 'div[class*="item"]', 'div[class*="card"]',
                'li[class*="product"]', 'li[class*="item"]'
            ]
            
            for selector in product_selectors:
                products = soup.select(selector)
                if products:
                    for product in products[:20]:  # Limit to 20 items per selector
                        item = self.extract_product_info(product, item_id)
                        if item:
                            menu_items.append(item)
                            item_id += 1
            
            # Pattern 2: Look for items with prices
            if not menu_items:
                menu_items = self.extract_by_price_patterns(soup, item_id)
            
            return menu_items
            
        except Exception as e:
            logger.debug(f"⚠️ Error scraping page {url}: {e}")
            return []
    
    def extract_product_info(self, product_element, item_id):
        """Extract product information from a product element"""
        try:
            # Extract name
            name = None
            name_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.title', '.name', '.product-title', '.product-name']
            for selector in name_selectors:
                name_elem = product_element.select_one(selector)
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    if name and len(name) > 2:
                        break
            
            if not name:
                # Try data attributes
                name = product_element.get('data-product-name') or product_element.get('data-name')
            
            if not name or len(name) < 2:
                return None
            
            # Extract price
            price = 0
            price_selectors = ['.price', '.amount', '.cost', '.product-price', 'span[class*="price"]', 'div[class*="price"]']
            price_text = ""
            
            for selector in price_selectors:
                price_elem = product_element.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    if price_text:
                        break
            
            if not price_text:
                # Look for price in the entire element text
                full_text = product_element.get_text()
                price_match = re.search(r'Rs\.?\s*([\d,]+)', full_text)
                if price_match:
                    price_text = price_match.group(0)
            
            # Parse price
            if price_text:
                price_match = re.search(r'([\d,]+(?:\.\d{2})?)', price_text.replace(',', ''))
                if price_match:
                    try:
                        price = float(price_match.group(1))
                    except:
                        price = 0
            
            if price <= 0:
                price = 300  # Default price
            
            # Extract description
            description = ""
            desc_selectors = ['.description', '.desc', '.product-desc', '.product-description']
            for selector in desc_selectors:
                desc_elem = product_element.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    break
            
            # Determine category
            category = self._determine_category(name)
            
            return {
                "id": item_id,
                "name": name[:100],
                "price": price,
                "category": category,
                "description": description[:200] if description else f"{category} item - Fresh and delicious",
                "is_available": True
            }
            
        except Exception as e:
            logger.debug(f"⚠️ Error extracting product: {e}")
            return None
    
    def extract_by_price_patterns(self, soup, start_id=1):
        """Extract menu items by looking for price patterns"""
        menu_items = []
        item_id = start_id
        
        # Look for text containing Rs. followed by numbers
        price_pattern = re.compile(r'([A-Za-z\s]+?)\s+Rs\.?\s*([\d,]+)', re.IGNORECASE)
        
        # Get all text and find price patterns
        all_text = soup.get_text()
        
        for match in price_pattern.finditer(all_text):
            item_name = match.group(1).strip()
            price_text = match.group(2).replace(',', '')
            
            if len(item_name) > 2:
                try:
                    price = float(price_text)
                    
                    menu_items.append({
                        "id": item_id,
                        "name": item_name[:100],
                        "price": price,
                        "category": self._determine_category(item_name),
                        "description": f"Fresh {item_name}",
                        "is_available": True
                    })
                    item_id += 1
                except:
                    continue
        
        return menu_items[:20]  # Limit to 20 items
    
    def extract_from_main_page(self, soup):
        """Extract menu items from main page content"""
        menu_items = []
        item_id = 1
        
        # Look for sections that might contain menu items
        sections = soup.find_all(['section', 'div', 'article'], 
                               class_=re.compile(r'menu|food|drink|product', re.I))
        
        for section in sections:
            # Look for headings that might be category names
            headings = section.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            for heading in headings:
                heading_text = heading.get_text(strip=True)
                if any(keyword in heading_text.lower() for keyword in ['menu', 'food', 'drink', 'coffee', 'tea']):
                    # This section might contain menu items
                    # Look for list items or paragraphs after the heading
                    next_elements = heading.find_next_siblings(['li', 'p', 'div'])
                    
                    for elem in next_elements[:10]:  # Check next 10 elements
                        text = elem.get_text(strip=True)
                        if text and len(text) > 10 and 'Rs' in text:
                            # Try to extract item name and price
                            parts = text.split('Rs')
                            if len(parts) >= 2:
                                item_name = parts[0].strip()
                                price_text = parts[1].strip()
                                price_match = re.search(r'([\d,]+)', price_text)
                                
                                if item_name and price_match:
                                    try:
                                        price = float(price_match.group(1).replace(',', ''))
                                        
                                        menu_items.append({
                                            "id": item_id,
                                            "name": item_name[:100],
                                            "price": price,
                                            "category": self._determine_category(item_name),
                                            "description": f"Fresh {item_name}",
                                            "is_available": True
                                        })
                                        item_id += 1
                                    except:
                                        continue
        
        return menu_items if menu_items else self.create_pakistani_menu()
    
    def _determine_category(self, item_name):
        """Determine category based on item name"""
        item_lower = item_name.lower()
        
        categories = {
            'Coffee': ['coffee', 'espresso', 'cappuccino', 'latte', 'americano', 'mocha', 'macchiato', 'flat white'],
            'Tea': ['tea', 'chai', 'green tea', 'herbal', 'oolong', 'earl grey', 'masala'],
            'Beverages': ['juice', 'smoothie', 'shake', 'lemonade', 'milkshake', 'frappe', 'cold', 'iced'],
            'Pastries': ['croissant', 'muffin', 'cake', 'pastry', 'cookie', 'brownie', 'donut', 'bread', 'bagel'],
            'Food': ['sandwich', 'burger', 'wrap', 'roll', 'pizza', 'pasta', 'salad', 'breakfast', 'lunch'],
            'Desserts': ['dessert', 'sweet', 'chocolate', 'ice cream', 'pie', 'tart', 'pudding'],
            'Pakistani': ['biryani', 'karahi', 'nihari', 'haleem', 'samosa', 'pakora', 'kebab', 'tikka'],
            'Fast Food': ['burger', 'fries', 'zinger', 'pizza', 'nuggets', 'wrap']
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in item_lower:
                    return category
        
        return "Other"
    
    def create_pakistani_menu(self):
        """Create Pakistani-style coffee shop menu - UPDATED WITH MORE ITEMS"""
        logger.info("✅ Creating enhanced Pakistani coffee shop menu...")
        
        pakistani_menu = [
            # Coffee
            {"id": 1, "name": "Espresso", "price": 250.0, "category": "Coffee", "description": "Strong black coffee shot", "is_available": True},
            {"id": 2, "name": "Cappuccino", "price": 350.0, "category": "Coffee", "description": "Coffee with steamed milk foam", "is_available": True},
            {"id": 3, "name": "Latte", "price": 400.0, "category": "Coffee", "description": "Smooth coffee with lots of milk", "is_available": True},
            {"id": 4, "name": "Americano", "price": 300.0, "category": "Coffee", "description": "Diluted espresso, similar to filter coffee", "is_available": True},
            {"id": 5, "name": "Mocha", "price": 450.0, "category": "Coffee", "description": "Chocolate coffee delight", "is_available": True},
            {"id": 6, "name": "Flat White", "price": 420.0, "category": "Coffee", "description": "Creamy coffee with microfoam", "is_available": True},
            
            # Tea
            {"id": 7, "name": "Doodh Patti Chai", "price": 180.0, "category": "Tea", "description": "Traditional Pakistani milk tea", "is_available": True},
            {"id": 8, "name": "Green Tea", "price": 150.0, "category": "Tea", "description": "Healthy antioxidant green tea", "is_available": True},
            {"id": 9, "name": "Masala Chai", "price": 200.0, "category": "Tea", "description": "Spiced tea with herbs", "is_available": True},
            {"id": 10, "name": "Kashmiri Chai", "price": 350.0, "category": "Tea", "description": "Pink tea with nuts", "is_available": True},
            
            # Beverages
            {"id": 11, "name": "Fresh Orange Juice", "price": 300.0, "category": "Beverages", "description": "Freshly squeezed orange juice", "is_available": True},
            {"id": 12, "name": "Mango Shake", "price": 350.0, "category": "Beverages", "description": "Creamy mango milkshake", "is_available": True},
            {"id": 13, "name": "Chocolate Shake", "price": 380.0, "category": "Beverages", "description": "Rich chocolate milkshake", "is_available": True},
            {"id": 14, "name": "Lemonade", "price": 200.0, "category": "Beverages", "description": "Fresh lemon juice with mint", "is_available": True},
            {"id": 15, "name": "Mineral Water", "price": 100.0, "category": "Beverages", "description": "Bottled mineral water", "is_available": True},
            
            # Pastries
            {"id": 16, "name": "Croissant", "price": 200.0, "category": "Pastries", "description": "Flaky French butter pastry", "is_available": True},
            {"id": 17, "name": "Chocolate Croissant", "price": 250.0, "category": "Pastries", "description": "Croissant with chocolate filling", "is_available": True},
            {"id": 18, "name": "Blueberry Muffin", "price": 250.0, "category": "Pastries", "description": "Fresh blueberry muffin", "is_available": True},
            {"id": 19, "name": "Chocolate Chip Cookie", "price": 150.0, "category": "Pastries", "description": "Freshly baked chocolate chip cookie", "is_available": True},
            {"id": 20, "name": "Brownie", "price": 280.0, "category": "Pastries", "description": "Chocolate brownie with walnuts", "is_available": True},
            
            # Pakistani Snacks
            {"id": 21, "name": "Samosa", "price": 80.0, "category": "Pakistani", "description": "Crispy potato filled samosa", "is_available": True},
            {"id": 22, "name": "Pakora", "price": 200.0, "category": "Pakistani", "description": "Vegetable fritters with chutney", "is_available": True},
            {"id": 23, "name": "Spring Roll", "price": 250.0, "category": "Pakistani", "description": "Crispy vegetable spring rolls", "is_available": True},
            {"id": 24, "name": "Chicken Roll", "price": 350.0, "category": "Pakistani", "description": "Chicken wrap with vegetables", "is_available": True},
            
            # Fast Food
            {"id": 25, "name": "Zinger Burger", "price": 550.0, "category": "Fast Food", "description": "Crispy chicken burger with special sauce", "is_available": True},
            {"id": 26, "name": "Chicken Burger", "price": 450.0, "category": "Fast Food", "description": "Grilled chicken burger", "is_available": True},
            {"id": 27, "name": "French Fries", "price": 250.0, "category": "Fast Food", "description": "Crispy golden fries", "is_available": True},
            {"id": 28, "name": "Chicken Nuggets", "price": 350.0, "category": "Fast Food", "description": "Crispy chicken nuggets with dip", "is_available": True},
            
            # Sandwiches
            {"id": 29, "name": "Club Sandwich", "price": 550.0, "category": "Food", "description": "Triple decker sandwich with chicken", "is_available": True},
            {"id": 30, "name": "Grilled Cheese Sandwich", "price": 400.0, "category": "Food", "description": "Melted cheese sandwich", "is_available": True},
            {"id": 31, "name": "Chicken Sandwich", "price": 450.0, "category": "Food", "description": "Grilled chicken sandwich with veggies", "is_available": True},
            
            # Desserts
            {"id": 32, "name": "Chocolate Cake Slice", "price": 350.0, "category": "Desserts", "description": "Rich chocolate cake slice", "is_available": True},
            {"id": 33, "name": "Cheesecake", "price": 450.0, "category": "Desserts", "description": "Creamy New York cheesecake", "is_available": True},
            {"id": 34, "name": "Gulab Jamun", "price": 200.0, "category": "Desserts", "description": "Sweet milk balls in syrup", "is_available": True},
            {"id": 35, "name": "Falooda", "price": 400.0, "category": "Desserts", "description": "Traditional Pakistani dessert drink", "is_available": True},
            
            # Main Course
            {"id": 36, "name": "Chicken Biryani", "price": 450.0, "category": "Pakistani", "description": "Traditional Pakistani biryani", "is_available": True},
            {"id": 37, "name": "Chicken Karahi", "price": 650.0, "category": "Pakistani", "description": "Spicy chicken curry", "is_available": True},
            {"id": 38, "name": "Chicken Tikka", "price": 600.0, "category": "Pakistani", "description": "Grilled chicken pieces", "is_available": True},
            {"id": 39, "name": "Beef Seekh Kabab", "price": 500.0, "category": "Pakistani", "description": "Minced beef kababs", "is_available": True},
            
            # Salads
            {"id": 40, "name": "Caesar Salad", "price": 500.0, "category": "Food", "description": "Fresh Caesar salad with dressing", "is_available": True},
            {"id": 41, "name": "Greek Salad", "price": 450.0, "category": "Food", "description": "Fresh vegetable salad with feta", "is_available": True},
            {"id": 42, "name": "Fruit Salad", "price": 350.0, "category": "Food", "description": "Seasonal fruit mix", "is_available": True}
        ]
        
        # Save to file
        self._save_menu(pakistani_menu)
        
        return pakistani_menu
    
    def _save_menu(self, menu_items):
        """Save menu to JSON file"""
        try:
            os.makedirs('data', exist_ok=True)
            file_path = 'data/scraped_menu.json'
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(menu_items, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Menu saved to {file_path}")
        except Exception as e:
            logger.error(f"❌ Error saving menu: {e}")