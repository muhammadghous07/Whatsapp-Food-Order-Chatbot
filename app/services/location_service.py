from haversine import haversine
import requests
import json
import os
from typing import List, Dict, Tuple, Optional
from geopy.geocoders import Nominatim
import time

class LocationService:
    def __init__(self):
        self.branches = self.get_default_branches()  # CHANGED from load_branches() to get_default_branches()
        self.geolocator = Nominatim(
            user_agent="foodexpress_pakistan_v1.0",
            timeout=10
        )
    
    def get_default_branches(self):  # NEW METHOD
        """Return default branches"""
        return [
            {
                "id": 1,
                "name": "FoodExpress Karachi",
                "address": "Tariq Road, Karachi, Pakistan",
                "latitude": 24.8607,
                "longitude": 67.0011,
                "phone": "+923001234567",
                "type": "restaurant",
                "cuisine": ["Fast Food", "Pakistani", "Beverages"],
                "rating": 4.3,
                "delivery_time": "25-35 mins"
            },
            {
                "id": 2,
                "name": "FoodExpress Lahore", 
                "address": "Liberty Market, Lahore, Pakistan",
                "latitude": 31.5204,
                "longitude": 74.3587,
                "phone": "+923001234568",
                "type": "restaurant",
                "cuisine": ["Fast Food", "Pakistani", "Grill"],
                "rating": 4.5,
                "delivery_time": "20-30 mins"
            },
            {
                "id": 3,
                "name": "FoodExpress Islamabad",
                "address": "F-7 Markaz, Islamabad, Pakistan",
                "latitude": 33.738045,
                "longitude": 73.084488,
                "phone": "+923001234569",
                "type": "restaurant",
                "cuisine": ["Pakistani", "Continental"],
                "rating": 4.4,
                "delivery_time": "30-40 mins"
            }
        ]
    
    def geocode_address(self, address: str) -> Tuple[Optional[float], Optional[float], str]:
        """Convert address to coordinates using OpenStreetMap Nominatim - FIXED"""
        try:
            # Clean and prepare address
            address = address.strip()
            
            # Add Pakistan if not specified
            if not any(word in address.lower() for word in ['pakistan', 'pak', 'pk']):
                address = f"{address}, Pakistan"
            
            print(f"📍 Attempting to geocode: {address[:50]}...")
            
            # Try with different formats
            variations = [
                address,
                address.replace('house no', 'house').replace('sector', 'sect'),
                address + ' city',
                address.split(',')[0] + ', Pakistan' if ',' in address else address
            ]
            
            for addr_variation in variations[:2]:  # Try only first 2 variations
                try:
                    location = self.geolocator.geocode(addr_variation, exactly_one=True, timeout=5)
                    if location:
                        print(f"   ✅ Geocoded: {addr_variation[:50]}... -> {location.latitude}, {location.longitude}")
                        return location.latitude, location.longitude, location.address
                except Exception as e:
                    print(f"   ⚠️ Geocoding variation failed: {e}")
                    continue
            
            # Fallback to city-based coordinates
            return self._fallback_geocode(address)
                
        except Exception as e:
            print(f"❌ Geocoding error: {e}")
            return self._fallback_geocode(address)
    
    def _fallback_geocode(self, address: str) -> Tuple[float, float, str]:
        """Fallback geocoding for common Pakistani cities - FIXED"""
        address_lower = address.lower()
        
        if 'karachi' in address_lower:
            return 24.8607, 67.0011, "Karachi, Pakistan"
        elif 'lahore' in address_lower:
            return 31.5204, 74.3587, "Lahore, Pakistan"
        elif 'islamabad' in address_lower:
            return 33.738045, 73.084488, "Islamabad, Pakistan"
        elif 'rawalpindi' in address_lower:
            return 33.5651, 73.0169, "Rawalpindi, Pakistan"
        elif 'faisalabad' in address_lower:
            return 31.4504, 73.1350, "Faisalabad, Pakistan"
        elif 'multan' in address_lower:
            return 30.1575, 71.5249, "Multan, Pakistan"
        elif 'peshawar' in address_lower:
            return 34.0151, 71.5249, "Peshawar, Pakistan"
        elif 'quetta' in address_lower:
            return 30.1798, 66.9750, "Quetta, Pakistan"
        elif 'hyderabad' in address_lower:
            return 25.3960, 68.3578, "Hyderabad, Pakistan"
        else:
            # Default to Karachi
            print(f"   ⚠️ Could not geocode '{address[:30]}...', defaulting to Karachi")
            return 24.8607, 67.0011, "Karachi, Pakistan (Default)"
    
    def find_nearest_branch(self, user_lat: float, user_lon: float, max_distance_km: float = 50.0):
        """Find nearest restaurant branch within maximum distance"""
        nearest_branch = None
        min_distance = float('inf')
        
        for branch in self.branches:
            branch_coords = (branch['latitude'], branch['longitude'])
            user_coords = (user_lat, user_lon)
            
            distance = haversine(user_coords, branch_coords)
            
            if distance < min_distance and distance <= max_distance_km:
                min_distance = distance
                nearest_branch = branch
        
        return nearest_branch, min_distance if nearest_branch else (None, None)
    
    def find_nearby_restaurants(self, user_lat: float, user_lon: float, radius_km: float = 5.0, limit: int = 10):
        """Find nearby restaurants using Overpass API - SIMPLIFIED VERSION"""
        try:
            # For demo purposes, return sample restaurants near the location
            # In production, you would use Overpass API
            
            # Calculate distances to our branches
            nearby_branches = []
            for branch in self.branches:
                distance = haversine((user_lat, user_lon), (branch['latitude'], branch['longitude']))
                if distance <= radius_km:
                    branch_with_distance = branch.copy()
                    branch_with_distance['distance_km'] = round(distance, 2)
                    branch_with_distance['type'] = 'our_branch'
                    nearby_branches.append(branch_with_distance)
            
            # Add some sample nearby restaurants
            sample_restaurants = [
                {
                    'name': 'Cafe Wagera',
                    'cuisine': 'Coffee, Snacks',
                    'address': 'Nearby Cafe',
                    'latitude': user_lat + 0.01,
                    'longitude': user_lon + 0.01,
                    'distance_km': 0.8,
                    'type': 'nearby_restaurant',
                    'phone': '+92 300 1234570',
                    'rating': 4.1,
                    'delivery_time': '15-25 mins'
                },
                {
                    'name': 'Butt Karahi',
                    'cuisine': 'Pakistani, Karahi',
                    'address': 'Nearby Restaurant',
                    'latitude': user_lat + 0.02,
                    'longitude': user_lon - 0.01,
                    'distance_km': 1.5,
                    'type': 'nearby_restaurant',
                    'phone': '+92 300 1234571',
                    'rating': 4.2,
                    'delivery_time': '40-50 mins'
                },
                {
                    'name': 'Pizza Hut',
                    'cuisine': 'Pizza, Italian',
                    'address': 'Fast Food Chain',
                    'latitude': user_lat - 0.01,
                    'longitude': user_lon + 0.02,
                    'distance_km': 2.1,
                    'type': 'nearby_restaurant',
                    'phone': '+92 300 1234572',
                    'rating': 4.0,
                    'delivery_time': '35-45 mins'
                }
            ]
            
            # Calculate distances for sample restaurants
            for restaurant in sample_restaurants:
                distance = haversine((user_lat, user_lon), (restaurant['latitude'], restaurant['longitude']))
                restaurant['distance_km'] = round(distance, 2)
            
            # Combine all restaurants
            all_restaurants = nearby_branches + sample_restaurants
            
            # Sort by distance
            all_restaurants.sort(key=lambda x: x['distance_km'])
            
            return all_restaurants[:limit]
            
        except Exception as e:
            print(f"❌ Error finding nearby restaurants: {e}")
            return []
    
    def get_nearby_options(self, user_lat: float, user_lon: float):
        """Get all nearby options (our branches + sample restaurants)"""
        return self.find_nearby_restaurants(user_lat, user_lon, radius_km=10, limit=8)
    
    def create_map_url(self, user_lat: float, user_lon: float, restaurants: List[Dict]):
        """Create OpenStreetMap URL with markers"""
        if not restaurants:
            return None
        
        # Create simple OSM URL with markers
        markers = []
        for i, restaurant in enumerate(restaurants[:5]):
            color = 'green' if restaurant.get('type') == 'our_branch' else 'blue'
            label = str(i + 1)
            markers.append(f"{restaurant['latitude']},{restaurant['longitude']},color:{color}%7Clabel:{label}")
        
        markers_str = '%7C'.join(markers)
        return f"https://www.openstreetmap.org/?mlat={user_lat}&mlon={user_lon}&zoom=13&layers=M&markers={markers_str}"
    
    def format_nearby_restaurants_text(self, user_lat: float, user_lon: float):
        """Format nearby restaurants information for WhatsApp"""
        nearby_options = self.get_nearby_options(user_lat, user_lon)
        
        if not nearby_options:
            return "❌ No restaurants found nearby. Please try a different location."
        
        text = "📍 **NEARBY RESTAURANTS** 📍\n\n"
        
        for i, option in enumerate(nearby_options[:6], 1):
            if option.get('type') == 'our_branch':
                text += f"{i}. 🏪 **{option['name']}**\n"
                text += f"   📍 {option.get('distance_km', 0)} km | ⭐ {option.get('rating', 4.0)} | ⏰ {option.get('delivery_time', '30-40 mins')}\n"
                text += f"   🍽️ {', '.join(option.get('cuisine', ['Pakistani']))}\n"
                text += f"   📞 {option.get('phone', 'Not available')}\n\n"
            else:
                text += f"{i}. 🏠 **{option['name']}**\n"
                text += f"   📍 {option.get('distance_km', 0)} km | 🍽️ {option.get('cuisine', 'Various')}\n"
                text += f"   🚚 Estimated: {option.get('delivery_time', '40-50 mins')}\n\n"
        
        # Add our recommendation
        text += "💡 **Recommendation:** For fastest delivery, choose FoodExpress branches (🏪).\n"
        text += "📍 To view on map, visit: https://openstreetmap.org\n\n"
        text += "To order from a specific restaurant, type its number (e.g., '1')"
        
        return text
    
    def get_branch_by_id(self, branch_id: int):
        """Get branch by ID"""
        for branch in self.branches:
            if branch['id'] == branch_id:
                return branch
        return None