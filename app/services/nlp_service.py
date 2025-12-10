from transformers import pipeline
import re
import json
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class NLPService:
    def __init__(self):
        # Define predefined variations BEFORE they're used
        self.predefined_variations = {
            'Espresso': ['espresso', 'expresso', 'short coffee', 'black coffee', 'strong coffee'],
            'Cappuccino': ['cappuccino', 'cappucino', 'capuccino', 'cappu', 'coffee with milk', 'frothy coffee'],
            'Latte': ['latte', 'late', 'milk coffee', 'milky coffee', 'cafe latte'],
            'Americano': ['americano', 'american coffee', 'long black', 'filter coffee'],
            'Mocha': ['mocha', 'chocolate coffee', 'mocha coffee', 'coffee with chocolate'],
            'Hot Chocolate': ['hot chocolate', 'chocolate', 'cocoa', 'drinking chocolate', 'choco drink'],
            'Iced Coffee': ['iced coffee', 'cold coffee', 'ice coffee', 'coffee with ice', 'chilled coffee'],
            'Fresh Orange Juice': ['orange juice', 'juice', 'orange', 'fresh orange', 'orange drink'],
            'Croissant': ['croissant', 'crossant', 'pastry', 'french pastry', 'butter croissant'],
            'Muffin': ['muffin', 'cake', 'cupcake', 'small cake', 'bun'],
            'Sandwich': ['sandwich', 'sandwitch', 'burger', 'sub', 'grilled sandwich'],
            'Salad': ['salad', 'fresh salad', 'green salad', 'vegetable salad', 'healthy salad'],
            'Cake Slice': ['cake', 'slice', 'pastry', 'cake piece', 'dessert'],
            'Cookie': ['cookie', 'biscuit', 'cookies', 'biscotti', 'sweet cookie']
        }
        
        # Hindi/Urdu numbers for multilingual support
        self.hindi_numbers = {
            'ek': 1, 'do': 2, 'teen': 3, 'char': 4, 'panch': 5,
            'che': 6, 'saat': 7, 'aath': 8, 'nau': 9, 'das': 10,
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10
        }

        # HuggingFace Models - Using Zero-shot Classification
        try:
            print("🚀 Loading HuggingFace Zero-shot Classification model...")
            self.zero_shot_classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli"
            )
            self.model_loaded = True
            print("✅ HuggingFace Zero-shot model loaded successfully!")
        except Exception as e:
            print(f"❌ HuggingFace model loading failed: {e}")
            print("🔧 Falling back to rule-based system")
            self.model_loaded = False
        
        # Load menu from scraper
        self.menu_items = self.load_menu_from_scraper()
        
        # Build food keywords from menu items
        self.food_keywords = self.build_food_keywords()
        
        # Build menu priority based on popularity
        self.menu_priority = self.build_menu_priority()

    def load_menu_from_scraper(self) -> List[Dict]:
        """Load menu from the scraper or use default"""
        try:
            # This would connect to your scraper
            from app.utils.scraper import MenuScraper
            scraper = MenuScraper()
            menu_data = scraper.scrape_menu()
            print(f"✅ Loaded {len(menu_data)} items from scraper")
            return menu_data
        except Exception as e:
            print(f"❌ Failed to load from scraper: {e}")
            print("🔧 Using default menu")
            return self.get_default_menu()
    
    def get_default_menu(self) -> List[Dict]:
        """Default menu items for coffee shop"""
        return [
            {"id": 1, "name": "Espresso", "category": "Coffee", "price": 250, "description": "Strong black coffee"},
            {"id": 2, "name": "Cappuccino", "category": "Coffee", "price": 350, "description": "Coffee with steamed milk foam"},
            {"id": 3, "name": "Latte", "category": "Coffee", "price": 400, "description": "Coffee with lots of milk"},
            {"id": 4, "name": "Americano", "category": "Coffee", "price": 300, "description": "Diluted espresso"},
            {"id": 5, "name": "Mocha", "category": "Coffee", "price": 450, "description": "Chocolate coffee drink"},
            {"id": 6, "name": "Hot Chocolate", "category": "Beverages", "price": 350, "description": "Rich chocolate drink"},
            {"id": 7, "name": "Iced Coffee", "category": "Cold Drinks", "price": 400, "description": "Chilled coffee with ice"},
            {"id": 8, "name": "Fresh Orange Juice", "category": "Juices", "price": 300, "description": "Freshly squeezed orange juice"},
            {"id": 9, "name": "Croissant", "category": "Pastries", "price": 200, "description": "Flaky French pastry"},
            {"id": 10, "name": "Muffin", "category": "Pastries", "price": 250, "description": "Sweet baked cake"},
            {"id": 11, "name": "Sandwich", "category": "Food", "price": 450, "description": "Grilled sandwich with filling"},
            {"id": 12, "name": "Salad", "category": "Food", "price": 500, "description": "Fresh vegetable salad"},
            {"id": 13, "name": "Cake Slice", "category": "Desserts", "price": 350, "description": "Slice of cake"},
            {"id": 14, "name": "Cookie", "category": "Desserts", "price": 150, "description": "Freshly baked cookie"}
        ]
    
    def build_food_keywords(self) -> Dict[str, List[str]]:
        """Build food keywords dictionary from menu items"""
        food_keywords = {}
        
        for item in self.menu_items:
            item_name = item['name']
            item_name_lower = item_name.lower()
            
            # Start with the item name itself
            keywords = [item_name_lower]
            
            # Add category-based keywords
            category = item.get('category', '').lower()
            if category:
                keywords.append(category)
                keywords.append(category + ' item')
            
            # Add word variations from the name
            words = item_name_lower.split()
            for word in words:
                if len(word) > 2 and word not in keywords:
                    keywords.append(word)
            
            # Add predefined variations if available
            if item_name in self.predefined_variations:
                keywords.extend(self.predefined_variations[item_name])
            
            # Add common abbreviations
            if 'espresso' in item_name_lower:
                keywords.extend(['expresso', 'short black'])
            elif 'cappuccino' in item_name_lower:
                keywords.extend(['cap', 'cappu', 'frothy'])
            elif 'latte' in item_name_lower:
                keywords.extend(['milk coffee', 'cafe latte'])
            elif 'americano' in item_name_lower:
                keywords.extend(['long black', 'american'])
            elif 'mocha' in item_name_lower:
                keywords.extend(['choc coffee', 'moca'])
            elif 'chocolate' in item_name_lower:
                keywords.extend(['choco', 'hot choc'])
            elif 'juice' in item_name_lower:
                keywords.extend(['fresh', 'squeezed'])
            elif 'croissant' in item_name_lower:
                keywords.extend(['crossant', 'french pastry'])
            elif 'muffin' in item_name_lower:
                keywords.extend(['small cake', 'cup cake'])
            elif 'sandwich' in item_name_lower:
                keywords.extend(['sandwitch', 'sub'])
            elif 'salad' in item_name_lower:
                keywords.extend(['veggies', 'greens'])
            elif 'cake' in item_name_lower:
                keywords.extend(['pastry', 'dessert'])
            elif 'cookie' in item_name_lower:
                keywords.extend(['biscuit', 'biscotti'])
            
            # Remove duplicates
            keywords = list(dict.fromkeys(keywords))
            food_keywords[item_name] = keywords
        
        print(f"✅ Built food keywords for {len(food_keywords)} menu items")
        return food_keywords
    
    def build_menu_priority(self) -> Dict[str, int]:
        """Build menu priority based on popularity"""
        priority_items = {
            'Espresso': 1,      # High priority - popular
            'Cappuccino': 1,    # High priority - very popular
            'Latte': 1,         # High priority - very popular
            'Americano': 2,     # Medium priority
            'Mocha': 2,         # Medium priority
            'Hot Chocolate': 3, # Low priority - seasonal
            'Iced Coffee': 2,   # Medium priority - seasonal
            'Fresh Orange Juice': 2, # Medium priority
            'Croissant': 1,     # High priority - popular breakfast
            'Muffin': 2,        # Medium priority
            'Sandwich': 1,      # High priority - lunch item
            'Salad': 3,         # Low priority
            'Cake Slice': 2,    # Medium priority
            'Cookie': 3         # Low priority
        }
        
        # Only include items that are in our menu
        menu_names = [item['name'] for item in self.menu_items]
        return {k: v for k, v in priority_items.items() if k in menu_names}

    def detect_intent(self, message: str) -> str:
        """Detect user intent using HuggingFace Zero-shot Classification"""
        message_lower = message.lower().strip()
        
        # Use HuggingFace Zero-shot classification if available
        if self.model_loaded:
            try:
                # Define possible intents for zero-shot classification
                candidate_labels = [
                    "place food order", 
                    "track order status",
                    "get branch information", 
                    "request help",
                    "greeting message",
                    "nearby restaurants",
                    "get menu"
                ]
                
                # Use zero-shot classification
                result = self.zero_shot_classifier(message_lower, candidate_labels)
                predicted_intent = result['labels'][0]
                confidence = result['scores'][0]
                
                print(f"🎯 HuggingFace Intent: {predicted_intent} (Confidence: {confidence:.2f})")
                
                # Map to our intent system
                intent_map = {
                    "place food order": "place_order",
                    "track order status": "track_order",
                    "get branch information": "branch_info", 
                    "request help": "help",
                    "greeting message": "greeting",
                    "nearby restaurants": "nearby_restaurants",
                    "get menu": "get_menu"
                }
                
                if confidence > 0.5:  # Only use if confident
                    return intent_map.get(predicted_intent, "place_order")
                    
            except Exception as e:
                print(f"❌ HuggingFace intent detection failed: {e}")
        
        # Fallback to rule-based system
        return self._rule_based_intent(message_lower)

    def _rule_based_intent(self, message: str) -> str:
        """Rule-based intent detection as fallback"""
        message_lower = message.lower()
        
        # Check for specific patterns
        if any(word in message_lower for word in ['nearby', 'close to', 'near me', 'around me', 'restaurants near']):
            return "nearby_restaurants"
        elif any(word in message_lower for word in ['order', 'want', 'need', 'would like', 'can i have', 'give me', 'i want']):
            return "place_order"
        elif any(word in message_lower for word in ['track', 'status', 'where is', 'when will', 'order status']):
            return "track_order" 
        elif any(word in message_lower for word in ['branch', 'shop', 'location', 'outlet', 'address', 'branches']):
            return "branch_info"
        elif any(word in message_lower for word in ['help', 'support', 'problem', 'issue']):
            return "help"
        elif any(word in message_lower for word in ['hello', 'hi', 'hey', 'start', 'good']):
            return "greeting"
        elif any(word in message_lower for word in ['menu', 'items', 'list', 'what do you have', 'offer', 'whats available']):
            return "get_menu"
        else:
            return "place_order"

    def extract_order_items(self, message: str) -> List[Dict]:
        """Extract food items and quantities using advanced NLP"""
        message_lower = message.lower()
        
        logger.info(f"🔍 NLP Processing: '{message_lower}'")
        
        # First try pattern matching
        items = self._improved_pattern_matching(message_lower)
        
        # If pattern matching found items, return them
        if items:
            logger.info(f"   📦 Pattern matched {len(items)} items")
            return items
        
        # Fallback to keyword matching
        items = self._keyword_matching(message_lower)
        
        logger.info(f"   📦 Final items: {items}")
        return items

    def _improved_pattern_matching(self, message: str) -> List[Dict]:
        """Improved pattern matching that prevents duplicates"""
        items = []
        processed_positions = set()
        
        # Define patterns with their priority
        patterns = [
            # High priority: AND pattern first (2 coffee and 1 cookie)
            (r'(\d+)\s+([a-zA-Z\s]+)\s+and\s+(\d+)\s+([a-zA-Z\s]+)', 'and_pattern', 1),
            
            # Medium priority: Quantity with item (2 coffee, 3x cookie)
            (r'(\d+)\s*(x|\*)?\s*([a-zA-Z\s]+)', 'quantity_item', 2),
            
            # Low priority: Hindi numbers (do coffee, one cookie)
            (r'(ek|do|teen|char|panch|one|two|three|four|five)\s+([a-zA-Z\s]+)', 'hindi_quantity', 3),
            
            # Special pattern: "I want X of Y"
            (r'i\s+want\s+(\d+)\s+of\s+([a-zA-Z\s]+)', 'i_want_pattern', 2),
            
            # Special pattern: "Give me X Y"
            (r'give\s+me\s+(\d+)\s+([a-zA-Z\s]+)', 'give_me_pattern', 2),
        ]
        
        # Sort patterns by priority
        patterns.sort(key=lambda x: x[2])
        
        for pattern, pattern_type, priority in patterns:
            matches = list(re.finditer(pattern, message))
            for match in matches:
                start, end = match.span()
                
                # Check if this position is already processed
                position_key = (start, end)
                if position_key in processed_positions:
                    continue
                
                processed_positions.add(position_key)
                
                if pattern_type == 'and_pattern':
                    quantity1 = int(match.group(1))
                    item_name1 = self._clean_item_name(match.group(2))
                    quantity2 = int(match.group(3))
                    item_name2 = self._clean_item_name(match.group(4))
                    
                    if item_name1:
                        self._add_or_update_item(items, item_name1, quantity1)
                        logger.info(f"   ✅ AND Pattern: {quantity1}x {item_name1}")
                    if item_name2:
                        self._add_or_update_item(items, item_name2, quantity2)
                        logger.info(f"   ✅ AND Pattern: {quantity2}x {item_name2}")
                
                elif pattern_type in ['quantity_item', 'i_want_pattern', 'give_me_pattern']:
                    quantity = int(match.group(1))
                    item_name = match.group(3) if pattern_type == 'quantity_item' else match.group(2)
                    item_name = item_name.strip()
                    item_name = self._clean_item_name(item_name)
                    if item_name:
                        self._add_or_update_item(items, item_name, quantity)
                        logger.info(f"   ✅ {pattern_type}: {quantity}x {item_name}")
                
                elif pattern_type == 'hindi_quantity':
                    quantity_text = match.group(1)
                    quantity = self.hindi_numbers.get(quantity_text.lower(), 1)
                    item_name = match.group(2).strip()
                    item_name = self._clean_item_name(item_name)
                    if item_name:
                        self._add_or_update_item(items, item_name, quantity)
                        logger.info(f"   ✅ Hindi Pattern: {quantity}x {item_name}")
        
        return items

    def _keyword_matching(self, message: str) -> List[Dict]:
        """Keyword matching for coffee shop items"""
        items = []
        matched_items = set()
        
        # Check for common phrases first
        common_phrases = {
            'i want coffee': [{'item': 'Espresso', 'quantity': 1}],
            'coffee please': [{'item': 'Espresso', 'quantity': 1}],
            'give me coffee': [{'item': 'Espresso', 'quantity': 1}],
            'i need coffee': [{'item': 'Espresso', 'quantity': 1}],
            'coffee and cookie': [{'item': 'Espresso', 'quantity': 1}, {'item': 'Cookie', 'quantity': 1}],
            'latte and croissant': [{'item': 'Latte', 'quantity': 1}, {'item': 'Croissant', 'quantity': 1}],
            'cappuccino and muffin': [{'item': 'Cappuccino', 'quantity': 1}, {'item': 'Muffin', 'quantity': 1}],
        }
        
        for phrase, phrase_items in common_phrases.items():
            if phrase in message:
                for item in phrase_items:
                    self._add_or_update_item(items, item['item'], item['quantity'])
                logger.info(f"   ✅ Common phrase: {phrase}")
                break
        
        # If no common phrase matched, try keyword matching
        if not items:
            # Look for menu items in the message
            for menu_item_name, keywords in self.food_keywords.items():
                if menu_item_name in matched_items:
                    continue
                    
                for keyword in keywords:
                    if keyword in message and menu_item_name not in matched_items:
                        # Check if there's a number before the keyword
                        pattern = r'(\d+)\s*' + re.escape(keyword)
                        number_match = re.search(pattern, message)
                        
                        if number_match:
                            quantity = int(number_match.group(1))
                        else:
                            quantity = 1
                        
                        self._add_or_update_item(items, menu_item_name, quantity)
                        matched_items.add(menu_item_name)
                        logger.info(f"   ✅ Keyword match: {quantity}x {menu_item_name}")
                        break
        
        return items

    def _add_or_update_item(self, items: List[Dict], item_name: str, quantity: int):
        """Add or update item in the list (prevents duplicates)"""
        # First, find the actual menu item name (case-insensitive)
        actual_item_name = None
        for menu_item in self.menu_items:
            if menu_item['name'].lower() == item_name.lower():
                actual_item_name = menu_item['name']
                break
        
        if not actual_item_name:
            # If not found in menu, use the provided name
            actual_item_name = item_name
        
        # Check if item already exists
        for item in items:
            if item['item'].lower() == actual_item_name.lower():
                item['quantity'] += quantity
                return
        
        # If item not found, add new one
        items.append({"item": actual_item_name, "quantity": quantity})

    def _clean_item_name(self, item_name: str) -> str:
        """Clean and normalize item names"""
        if not item_name:
            return ""
            
        # Remove common stop words
        stop_words = [
            'and', 'with', 'want', 'order', 'i', 'to', 'please', 'for', 'me', 
            'give', 'get', 'need', 'would like', 'can i have', 'may i have',
            'a', 'an', 'the', 'some', 'any'
        ]
        
        words = item_name.split()
        cleaned_words = [word for word in words if word.lower() not in stop_words]
        
        cleaned_name = ' '.join(cleaned_words).strip()
        
        if not cleaned_name:
            return ""
        
        # Check if the cleaned name matches any menu item directly
        for menu_item in self.menu_items:
            if menu_item['name'].lower() == cleaned_name.lower():
                return menu_item['name']
        
        # Check if cleaned name is in keywords of any menu item
        for menu_item_name, keywords in self.food_keywords.items():
            if cleaned_name.lower() in [k.lower() for k in keywords]:
                return menu_item_name
        
        # Try fuzzy matching with menu items
        best_match = None
        best_score = 0.6
        
        for menu_item in self.menu_items:
            similarity = self._similarity(cleaned_name.lower(), menu_item['name'].lower())
            if similarity > best_score:
                best_score = similarity
                best_match = menu_item['name']
        
        if best_match:
            return best_match
        
        # Return the cleaned name as is
        return cleaned_name

    def validate_menu_items(self, extracted_items: List[Dict], menu_data: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """Validate extracted items against menu with improved fuzzy matching"""
        validated_items = []
        invalid_items = []
        
        logger.info(f"🔍 Validating {len(extracted_items)} items against menu...")
        
        # Create a mapping of menu items for faster lookup
        menu_map = {item['name']: item for item in menu_data}
        
        for item in extracted_items:
            best_match = self._find_best_menu_match(item['item'], menu_map)
            
            if best_match:
                menu_item = menu_map[best_match]
                validated_items.append({
                    'menu_item_id': menu_item['id'],
                    'name': menu_item['name'],
                    'quantity': item['quantity'],
                    'price': float(menu_item['price']),
                    'total_price': float(menu_item['price']) * item['quantity'],
                    'category': menu_item.get('category', 'Unknown')
                })
                logger.info(f"   ✅ Validated: '{item['item']}' -> '{menu_item['name']}'")
            else:
                invalid_items.append(item['item'])
                logger.info(f"   ❌ Not found: '{item['item']}'")
        
        logger.info(f"   📊 Result: {len(validated_items)} valid, {len(invalid_items)} invalid")
        return validated_items, invalid_items

    def _find_best_menu_match(self, extracted: str, menu_map: Dict) -> Optional[str]:
        """Find the best matching menu item using multiple strategies"""
        extracted_lower = extracted.lower()
        
        # Strategy 1: Direct exact match
        for menu_name in menu_map.keys():
            if extracted_lower == menu_name.lower():
                return menu_name
        
        # Strategy 2: Check if extracted is in keywords
        for menu_name, keywords in self.food_keywords.items():
            if menu_name in menu_map:  # Ensure menu item exists in current menu
                for keyword in keywords:
                    if extracted_lower == keyword.lower():
                        return menu_name
        
        # Strategy 3: Substring match
        for menu_name in menu_map.keys():
            menu_lower = menu_name.lower()
            if extracted_lower in menu_lower or menu_lower in extracted_lower:
                return menu_name
        
        # Strategy 4: Keyword presence in extracted text
        for menu_name, keywords in self.food_keywords.items():
            if menu_name in menu_map:
                for keyword in keywords:
                    if keyword.lower() in extracted_lower:
                        return menu_name
        
        # Strategy 5: Fuzzy matching with similarity score
        best_match = None
        best_score = 0.6  # Minimum similarity threshold
        
        for menu_name in menu_map.keys():
            menu_lower = menu_name.lower()
            similarity = self._similarity(extracted_lower, menu_lower)
            
            # Apply priority boost if available
            priority_boost = self.menu_priority.get(menu_name, 0) * 0.05
            adjusted_similarity = similarity + priority_boost
            
            if adjusted_similarity > best_score:
                best_score = adjusted_similarity
                best_match = menu_name
        
        # Strategy 6: Check word overlap
        if not best_match:
            extracted_words = set(extracted_lower.split())
            best_overlap = 0
            
            for menu_name in menu_map.keys():
                menu_words = set(menu_name.lower().split())
                overlap = len(extracted_words.intersection(menu_words))
                
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match = menu_name
        
        return best_match

    def _similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, a, b).ratio()

    def find_menu_item(self, item_text: str, variations: Dict = None) -> Optional[Dict]:
        """Find menu item by text with variations"""
        if variations is None:
            variations = {}
        
        item_text_lower = item_text.lower()
        
        # Direct match
        for menu_item in self.menu_items:
            if menu_item['name'].lower() == item_text_lower:
                return menu_item
        
        # Check variations
        for menu_item in self.menu_items:
            menu_name_lower = menu_item['name'].lower()
            
            # Check predefined variations
            if menu_name_lower in variations:
                for variation in variations[menu_name_lower]:
                    if variation in item_text_lower:
                        return menu_item
            
            # Check built-in keywords
            if menu_item['name'] in self.food_keywords:
                for keyword in self.food_keywords[menu_item['name']]:
                    if keyword in item_text_lower:
                        return menu_item
        
        return None

    def calculate_order_total(self, validated_items: List[Dict]) -> float:
        """Calculate total order amount"""
        total = sum(item['total_price'] for item in validated_items)
        logger.info(f"💰 Calculated total: {total}")
        return total

    def get_menu_categories(self) -> List[str]:
        """Get unique menu categories"""
        categories = set()
        for item in self.menu_items:
            categories.add(item.get('category', 'Other'))
        return sorted(list(categories))

    def search_menu_items(self, query: str, category: str = None) -> List[Dict]:
        """Search menu items by query and optional category"""
        query_lower = query.lower()
        results = []
        
        for item in self.menu_items:
            # Filter by category if specified
            if category and item.get('category') != category:
                continue
            
            # Check name
            if query_lower in item['name'].lower():
                results.append(item)
                continue
            
            # Check description
            description = item.get('description', '').lower()
            if query_lower in description:
                results.append(item)
                continue
            
            # Check keywords
            if item['name'] in self.food_keywords:
                for keyword in self.food_keywords[item['name']]:
                    if query_lower in keyword.lower():
                        results.append(item)
                        break
        
        return results

    def get_menu_for_display(self) -> str:
        """Format menu for display"""
        if not self.menu_items:
            return "❌ No menu items available."
        
        # Group by category
        categories = {}
        for item in self.menu_items:
            category = item.get('category', 'Other')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        menu_text = "☕ **OUR MENU** ☕\n\n"
        
        for category, items in categories.items():
            menu_text += f"**{category}**\n"
            for item in items:
                menu_text += f"• **{item['name']}** - Rs. {item['price']:,.0f}\n"
                if item.get('description'):
                    menu_text += f"  _{item['description']}_\n"
            menu_text += "\n"
        
        menu_text += "📝 **How to order:**\n"
        menu_text += "Simply type what you want! Examples:\n"
        menu_text += "• '2 cappuccino 1 cookie'\n"
        menu_text += "• 'I want a latte and croissant'\n"
        menu_text += "• 'One espresso please'\n"
        
        return menu_text

# Global instance for easy import - REMOVED to prevent auto-initialization
nlp_service = NLPService()