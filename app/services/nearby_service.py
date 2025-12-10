import requests
import os
from typing import List, Dict, Optional
import logging
from haversine import haversine
import json

logger = logging.getLogger(__name__)

class NearbyRestaurantService:
    def __init__(self):
        self.google_places_api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
        self.use_google_api = bool(self.google_places_api_key)
        
        # Our restaurant database (you can expand this)
        self.restaurant_database = [
            {
                "id": 1,
                "name": "FoodExpress Karachi",
                "address": "Tariq Road, Karachi",
                "latitude": 24.8607,
                "longitude": 67.0011,
                "cuisine": ["Pakistani", "Fast Food", "BBQ"],
                "rating": 4.2,
                "delivery_time": "30-45 min",
                "min_order": 300,
                "phone": "+923001234567",
                "is_open": True
            },
            {
                "id": 2,
                "name": "FoodExpress Lahore",
                "address": "Liberty Market, Lahore",
                "latitude": 31.5204,
                "longitude": 74.3587,
                "cuisine": ["Pakistani", "Chinese", "Fast Food"],
                "rating": 4.5,
                "delivery_time": "25-40 min",
                "min_order": 350,
                "phone": "+923001234568",
                "is_open": True
            },
            {
                "id": 3,
                "name": "FoodExpress Islamabad",
                "address": "F-7 Markaz, Islamabad",
                "latitude": 33.738045,
                "longitude": 73.084488,
                "cuisine": ["Pakistani", "Continental", "BBQ"],
                "rating": 4.3,
                "delivery_time": "35-50 min",
                "min_order": 400,
                "phone": "+923001234569",
                "is_open": True
            },
            {
                "id": 4,
                "name": "Karachi Biryani Point",
                "address": "Saddar, Karachi",
                "latitude": 24.8500,
                "longitude": 67.0200,
                "cuisine": ["Biryani", "Pakistani"],
                "rating": 4.1,
                "delivery_time": "40-55 min",
                "min_order": 500,
                "phone": "+923001234570",
                "is_open": True
            },
            {
                "id": 5,
                "name": "Lahore Karahi House",
                "address": "Gulberg, Lahore",
                "latitude": 31.5250,
                "longitude": 74.3400,
                "cuisine": ["Karahi", "BBQ", "Pakistani"],
                "rating": 4.4,
                "delivery_time": "30-45 min",
                "min_order": 600,
                "phone": "+923001234571",
                "is_open": True
            }
        ]
    
    def find_nearby_restaurants(self, user_lat: float, user_lon: float, radius_km: float = 5.0, 
                                cuisine_filter: Optional[str] = None, max_results: int = 10) -> List[Dict]:
        """Find restaurants near user location"""
        nearby_restaurants = []
        
        for restaurant in self.restaurant_database:
            # Calculate distance
            restaurant_coords = (restaurant['latitude'], restaurant['longitude'])
            user_coords = (user_lat, user_lon)
            
            distance = haversine(user_coords, restaurant_coords)
            
            # Check if within radius
            if distance <= radius_km:
                restaurant_copy = restaurant.copy()
                restaurant_copy['distance_km'] = round(distance, 2)
                restaurant_copy['distance_text'] = self._format_distance(distance)
                
                # Apply cuisine filter if provided
                if cuisine_filter:
                    if cuisine_filter.lower() in [c.lower() for c in restaurant['cuisine']]:
                        nearby_restaurants.append(restaurant_copy)
                else:
                    nearby_restaurants.append(restaurant_copy)
        
        # Sort by distance
        nearby_restaurants.sort(key=lambda x: x['distance_km'])
        
        return nearby_restaurants[:max_results]
    
    def find_nearby_restaurants_google(self, user_lat: float, user_lon: float, radius_meters: int = 5000,
                                      cuisine_type: Optional[str] = None) -> List[Dict]:
        """Find nearby restaurants using Google Places API"""
        if not self.use_google_api:
            logger.warning("Google Places API key not configured")
            return []
        
        try:
            base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            
            params = {
                "key": self.google_places_api_key,
                "location": f"{user_lat},{user_lon}",
                "radius": radius_meters,
                "type": "restaurant",
                "rankby": "prominence"
            }
            
            if cuisine_type:
                params["keyword"] = cuisine_type
            
            response = requests.get(base_url, params=params, timeout=10)
            data = response.json()
            
            restaurants = []
            
            if data.get("status") == "OK":
                for place in data.get("results", []):
                    restaurant = {
                        "name": place.get("name", "Unknown"),
                        "address": place.get("vicinity", "Address not available"),
                        "latitude": place["geometry"]["location"]["lat"],
                        "longitude": place["geometry"]["location"]["lng"],
                        "rating": place.get("rating", 0),
                        "total_ratings": place.get("user_ratings_total", 0),
                        "is_open": place.get("opening_hours", {}).get("open_now", True),
                        "place_id": place.get("place_id"),
                        "types": place.get("types", []),
                        "price_level": place.get("price_level", 0),
                        "distance_km": self._calculate_google_distance(user_lat, user_lon, 
                                                                      place["geometry"]["location"]["lat"],
                                                                      place["geometry"]["location"]["lng"])
                    }
                    
                    # Format distance text
                    restaurant['distance_text'] = self._format_distance(restaurant['distance_km'])
                    restaurants.append(restaurant)
            
            return restaurants[:10]  # Return top 10
            
        except Exception as e:
            logger.error(f"Google Places API error: {e}")
            return []
    
    def get_restaurant_details(self, restaurant_id: int) -> Optional[Dict]:
        """Get detailed information about a specific restaurant"""
        for restaurant in self.restaurant_database:
            if restaurant['id'] == restaurant_id:
                return restaurant
        return None
    
    def get_restaurant_menu(self, restaurant_id: int) -> List[Dict]:
        """Get menu for a specific restaurant"""
        # This would typically come from a database
        # For now, return a sample menu based on restaurant type
        restaurant = self.get_restaurant_details(restaurant_id)
        
        if not restaurant:
            return []
        
        # Sample menus based on cuisine
        base_menu = [
            {"id": 1, "name": "Chicken Biryani", "price": 450, "category": "Main Course"},
            {"id": 2, "name": "Beef Burger", "price": 550, "category": "Fast Food"},
            {"id": 3, "name": "Chicken Karahi", "price": 1200, "category": "Main Course"},
            {"id": 4, "name": "Zinger Burger", "price": 650, "category": "Fast Food"},
            {"id": 5, "name": "Chicken Roll", "price": 220, "category": "Snacks"},
            {"id": 6, "name": "Samosa", "price": 80, "category": "Snacks"},
            {"id": 7, "name": "Doodh Patti Chai", "price": 120, "category": "Beverages"},
            {"id": 8, "name": "Mango Shake", "price": 300, "category": "Beverages"},
        ]
        
        # Add restaurant-specific items
        if "Biryani" in restaurant['name']:
            base_menu.extend([
                {"id": 9, "name": "Special Beef Biryani", "price": 600, "category": "Main Course"},
                {"id": 10, "name": "Chicken Pulao", "price": 400, "category": "Main Course"},
            ])
        
        return base_menu
    
    def _format_distance(self, distance_km: float) -> str:
        """Format distance in readable text"""
        if distance_km < 1:
            meters = int(distance_km * 1000)
            return f"{meters}m away"
        elif distance_km < 10:
            return f"{distance_km:.1f}km away"
        else:
            return f"{int(distance_km)}km away"
    
    def _calculate_google_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates for Google results"""
        from haversine import haversine
        return haversine((lat1, lon1), (lat2, lon2))
    
    def format_restaurants_for_display(self, restaurants: List[Dict]) -> str:
        """Format restaurant list for display in WhatsApp/Streamlit"""
        if not restaurants:
            return "❌ No restaurants found near your location. Try a different address."
        
        message = "🍽️ *RESTAURANTS NEAR YOU*\n\n"
        
        for idx, restaurant in enumerate(restaurants[:5], 1):  # Show top 5
            status = "🟢 OPEN" if restaurant.get('is_open', True) else "🔴 CLOSED"
            rating = restaurant.get('rating', 'N/A')
            
            message += f"{idx}. *{restaurant['name']}*\n"
            message += f"   📍 {restaurant['distance_text']}\n"
            message += f"   ⭐ {rating}/5"
            if restaurant.get('total_ratings'):
                message += f" ({restaurant['total_ratings']} reviews)"
            message += f"\n"
            message += f"   🚚 {restaurant.get('delivery_time', '30-45 min')}\n"
            message += f"   💰 Min: Rs. {restaurant.get('min_order', 300)}\n"
            
            # Add cuisine types if available
            if restaurant.get('cuisine'):
                message += f"   🍴 {', '.join(restaurant['cuisine'][:3])}\n"
            
            message += f"   {status}\n\n"
        
        message += "📝 *How to order:*\n"
        message += "Type the restaurant number (1-5) to view menu\n"
        message += "Or type 'menu' to see all available items"
        
        return message

# Global instance
nearby_service = NearbyRestaurantService()