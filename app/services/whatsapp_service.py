import json
import requests
from fastapi import HTTPException
import os
from typing import Dict, List, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.green_api_id = os.getenv("GREEN_API_ID", "").strip()
        self.green_api_token = os.getenv("GREEN_API_TOKEN", "").strip()
        self.green_api_url = "https://api.green-api.com"
        
        # Check if GREEN-API credentials are available
        self.green_api_enabled = bool(self.green_api_id and self.green_api_token)
        
        # Debug environment variables
        self.check_environment_variables()  # Add this line
        
        if self.green_api_enabled:
            logger.info("✅ GREEN-API WhatsApp Service Enabled")
            logger.info(f"📱 Instance ID: {self.green_api_id}")
        else:
            logger.info("🔶 GREEN-API not configured, running in DEMO mode")
    
    def check_environment_variables(self):
        """Debug method to check environment variables"""
        logger.info("🔍 Checking Environment Variables:")
        logger.info(f"   GREEN_API_ID: {os.getenv('GREEN_API_ID', 'NOT FOUND')}")
        logger.info(f"   GREEN_API_TOKEN: {os.getenv('GREEN_API_TOKEN', 'NOT FOUND')}")
        logger.info(f"   GREEN_API_ENABLED: {self.green_api_enabled}")
    
    def send_text_message(self, to: str, message: str) -> Dict:
        """Send text message using GREEN-API"""
        if not self.green_api_enabled:
            return self._demo_send_message(to, message, "text")
        
        url = f"{self.green_api_url}/waInstance{self.green_api_id}/sendMessage/{self.green_api_token}"
        
        # Format phone number (remove + and spaces)
        formatted_to = to.replace('+', '').replace(' ', '')
        
        payload = {
            "chatId": f"{formatted_to}@c.us",
            "message": message
        }
        
        try:
            logger.info(f"📤 Sending WhatsApp message to {formatted_to}")
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ Message sent successfully: {result.get('idMessage', 'Unknown')}")
            return {"status": "sent", "green_api": True, "message_id": result.get('idMessage')}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ GREEN-API Error: {e}")
            # Fallback to demo mode
            return self._demo_send_message(to, message, "text")
    
    def send_buttons_message(self, to: str, message: str, buttons: List[Dict]) -> Dict:
        """Send message with buttons using GREEN-API"""
        if not self.green_api_enabled:
            return self._demo_send_message(to, message, "buttons", buttons)
        
        url = f"{self.green_api_url}/waInstance{self.green_api_id}/sendButtons/{self.green_api_token}"
        
        formatted_to = to.replace('+', '').replace(' ', '')
        
        # Prepare buttons for GREEN-API
        green_buttons = []
        for i, button in enumerate(buttons[:3]):  # Max 3 buttons
            green_buttons.append({
                "buttonId": button.get('id', f'btn_{i+1}'),
                "buttonText": {
                    "displayText": button.get('title', f'Button {i+1}')
                }
            })
        
        payload = {
            "chatId": f"{formatted_to}@c.us",
            "message": message,
            "buttons": green_buttons,
            "footer": "FoodExpress Pakistan 🍕"
        }
        
        try:
            logger.info(f"📤 Sending buttons message to {formatted_to}")
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ Buttons message sent: {result.get('idMessage', 'Unknown')}")
            return {"status": "sent", "green_api": True, "message_id": result.get('idMessage')}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ GREEN-API Buttons Error: {e}")
            return self._demo_send_message(to, message, "buttons", buttons)
    
    def send_image_message(self, to: str, image_url: str, caption: str = "") -> Dict:
        """Send image message using GREEN-API"""
        if not self.green_api_enabled:
            return self._demo_send_message(to, f"🖼️ Image: {image_url}\n{caption}", "image")
        
        url = f"{self.green_api_url}/waInstance{self.green_api_id}/sendFileByUrl/{self.green_api_token}"
        
        formatted_to = to.replace('+', '').replace(' ', '')
        
        payload = {
            "chatId": f"{formatted_to}@c.us",
            "urlFile": image_url,
            "fileName": "menu_image.jpg",
            "caption": caption
        }
        
        try:
            logger.info(f"📤 Sending image to {formatted_to}")
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ Image sent: {result.get('idMessage', 'Unknown')}")
            return {"status": "sent", "green_api": True, "message_id": result.get('idMessage')}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ GREEN-API Image Error: {e}")
            return self._demo_send_message(to, f"🖼️ Image: {image_url}\n{caption}", "image")
    
    def get_message_status(self, message_id: str) -> Dict:
        """Get delivery status of a message"""
        if not self.green_api_enabled:
            return {"status": "delivered", "demo": True}
        
        url = f"{self.green_api_url}/waInstance{self.green_api_id}/getMessageInfo/{self.green_api_token}"
        
        payload = {
            "chatId": message_id  # This should be the chatId, not message id in this context
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.json()
        except:
            return {"status": "unknown"}
    
    def _demo_send_message(self, to: str, message: str, message_type: str = "text", buttons: List = None):
        """Demo mode for testing without GREEN-API"""
        logger.info(f"📱 DEMO WhatsApp to {to}:")
        logger.info("=" * 60)
        
        if message_type == "text":
            logger.info(f"💬 {message}")
        elif message_type == "buttons":
            logger.info(f"🔘 {message}")
            if buttons:
                for button in buttons:
                    logger.info(f"   - {button.get('title', 'Button')}")
        elif message_type == "image":
            logger.info(f"🖼️ {message}")
        
        logger.info("=" * 60)
        return {"status": "sent", "demo": True, "message": "DEMO MODE - No actual WhatsApp sent"}
    
    def create_welcome_message(self):
        """Create welcome message with buttons - Roman Urdu"""
        welcome_text = """🍕 *FoodExpress Pakistan Mein Aapka Swagat Hai!* 🎉

Aap kya karna pasand karenge?"""
        
        buttons = [
            {"id": "order_food", "title": "🍴 Order Karein"},
            {"id": "track_order", "title": "📦 Order Status"}, 
            {"id": "branch_info", "title": "📍 Branches"}
        ]
        
        return welcome_text, buttons
    
    def create_location_request(self):
        """Create message asking for location - Roman Urdu"""
        return """📍 *Location Share Karein*

Meharbani karke apna location share karein. Issey hum aapke sabse qareeb restaurant mein order bhej sakenge.

*WhatsApp par location share karne ka tareeka:*
1. Message box ke pass 📎 *attachment* icon par click karein
2. *Location* select karein  
3. *Share your current location* choose karein

Shukriya! 😊"""
    
    def create_order_summary(self, order_items: list, total_amount: float, branch_name: str, distance: float):
        """Create detailed order summary in Roman Urdu"""
        items_text = "\n".join([
            f"• {item['quantity']}x {item['name']} - Rs. {item['total_price']:,.0f}" 
            for item in order_items
        ])
        
        summary = f"""📋 *ORDER SUMMARY*

{items_text}

────────────────
💰 *Total Amount: Rs. {total_amount:,.0f}*
📍 *Nearest Branch: {branch_name}* ({distance:.1f} km door)

✅ Order confirm karne ke liye 'confirm' type karein
❌ Cancel karne ke liye 'cancel' type karein"""

        return summary
    
    def create_menu_list(self, menu_items: list):
        """Create formatted menu list with Pakistani prices - Roman Urdu"""
        if not menu_items:
            return "❌ Maaf karein, filhal koi menu items available nahi hain."
        
        menu_text = "🍽️ *HAMARA PAKISTANI MENU* 🍽️\n\n"
        
        # Group by category
        categories = {}
        for item in menu_items:
            if not item.get('name') or item.get('name') == 'string' or item.get('price', 0) <= 0:
                continue
                
            category = item.get('category', 'Other')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        # Show categories with valid items
        for category, items in categories.items():
            if items:
                menu_text += f"*{category}*\n"
                for item in items:
                    menu_text += f"• {item['name']} - Rs. {item['price']:,.0f}\n"
                menu_text += "\n"
        
        menu_text += "🍴 *Order kaise karein:*\n"
        menu_text += "Bas type karein aap kya lena chahte hain!\n\n"
        menu_text += "*Examples:*\n"
        menu_text += "• '2 chai aur 1 samosa'\n"
        menu_text += "• 'Mujhe 1 zinger burger chahiye'\n" 
        menu_text += "• '1 chicken biryani order karna hai'\n"
        menu_text += "• 'Chai samosa'\n"
        
        return menu_text
    
    def send_order_confirmation(self, to: str, order_id: int, total_amount: float):
        """Send order confirmation message - Roman Urdu"""
        message = f"""✅ *Order Successful!*

🎉 Aapka order #{order_id} confirm ho gaya hai!

💰 *Total Amount: Rs. {total_amount:,.0f}*

📦 Aapka order tayyar hone mein 20-25 minutes ka time lagega.

Aap 'track order #{order_id}' type karke apne order ka status check kar sakte hain.

FoodExpress Pakistan ka shukriya! 😊"""

        return self.send_text_message(to, message)
    
    def send_order_status(self, to: str, order_id: int, status: str, branch_name: str):
        """Send order status update - Roman Urdu"""
        status_messages = {
            "pending": "⏳ Aapka order receive ho gaya hai",
            "confirmed": "👨‍🍳 Aapka order tayyar ho raha hai",
            "preparing": "🔥 Aapka order kitchen mein hai", 
            "ready": "✅ Aapka order tayyar hai",
            "completed": "🎉 Aapka order complete ho gaya hai"
        }
        
        message = f"""📦 *Order #{order_id} Status*

{status_messages.get(status, "Aapka order process ho raha hai")}

📍 Branch: {branch_name}

Shukriya! FoodExpress Pakistan"""

        return self.send_text_message(to, message)
    
    def check_whatsapp_health(self) -> Dict:
        """Check if GREEN-API is working properly"""
        if not self.green_api_enabled:
            return {"status": "demo_mode", "message": "Running in DEMO mode"}
        
        url = f"{self.green_api_url}/waInstance{self.green_api_id}/getStateInstance/{self.green_api_token}"
        
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            return {
                "status": "connected",
                "whatsapp_state": data.get('stateInstance'),
                "green_api": True
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "green_api": True}