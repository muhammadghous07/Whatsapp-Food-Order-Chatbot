import streamlit as st
import requests
import time
from datetime import datetime
import json
import numpy as np
import tempfile
import os
from audio_recorder_streamlit import audio_recorder
from app.services.voice_service import voice_service

# FastAPI backend URL
API_BASE_URL = "http://localhost:8000"

class FoodExpressChatbot:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.session = requests.Session()
        self.session.timeout = (10, 30)
        self._last_request = None
        
    def send_message(self, message: str, phone_number: str):
        """Send message to chatbot - WITH DUPLICATE PROTECTION"""
        try:
            # Check if this is a duplicate request (within 3 seconds)
            current_time = time.time()
            if (self._last_request and 
                self._last_request.get('message') == message and 
                self._last_request.get('phone') == phone_number and
                current_time - self._last_request.get('time', 0) < 3):
                print(f"🛑 Blocked duplicate message: {message}")
                return {"status": "success", "message": "Duplicate blocked"}
            
            # Store current request
            self._last_request = {
                'message': message,
                'phone': phone_number,
                'time': current_time
            }
            
            print(f"📤 Sending message: {message} to {phone_number}")
            response = self.session.post(
                f"{self.base_url}/api/v1/demo/chat",
                json={
                    "message": message, 
                    "phone_number": phone_number
                },
                timeout=30
            )
            print(f"✅ Response received: {response.status_code}")
            return response.json()
        except requests.exceptions.Timeout:
            print("❌ Request timeout")
            return {"status": "error", "message": "Request timeout - backend is not responding"}
        except requests.exceptions.ConnectionError:
            print("❌ Connection error")
            return {"status": "error", "message": "Cannot connect to backend - make sure server is running on port 8000"}
        except Exception as e:
            print(f"❌ Other error: {e}")
            return {"status": "error", "message": f"Error: {str(e)}"}
    
    def get_conversations(self, phone_number: str):
        """Get conversation history"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/conversations/{phone_number}", 
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            return {"conversations": []}
        except Exception as e:
            print(f"❌ Error getting conversations: {e}")
            return {"conversations": []}
    
    def get_orders(self, phone_number: str):
        """Get order history"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/orders/{phone_number}", 
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            return {"orders": []}
        except Exception as e:
            print(f"❌ Error getting orders: {e}")
            return {"orders": []}
    
    def get_menu(self):
        """Get menu items - FIXED VERSION"""
        try:
            response = self.session.get(f"{self.base_url}/menu", timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                # Check different possible response formats
                if isinstance(data, dict):
                    # Format 1: Direct menu list
                    if 'menu' in data and isinstance(data['menu'], list):
                        return data['menu']
                    
                    # Format 2: Menu by category (from main.py endpoint)
                    elif 'menu_by_category' in data and isinstance(data['menu_by_category'], dict):
                        # Flatten the categories into a single list
                        flattened_menu = []
                        for category, items in data['menu_by_category'].items():
                            if isinstance(items, list):
                                for item in items:
                                    # Ensure item has required fields
                                    if isinstance(item, dict) and 'name' in item:
                                        flattened_menu.append(item)
                        return flattened_menu
                    
                    # Format 3: Try to find any list containing menu items
                    else:
                        for key, value in data.items():
                            if isinstance(value, list) and value:
                                # Check if first item looks like a menu item
                                first_item = value[0]
                                if isinstance(first_item, dict) and 'name' in first_item and 'price' in first_item:
                                    return value
                return []
            return []
        except Exception as e:
            print(f"❌ Error getting menu: {e}")
            return []
    
    def check_health(self):
        """Check backend health - SIMPLE VERSION"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

    def get_user_state(self, phone_number: str):
        """Get current user state for voice order confirmation"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/webhook/user-state/{phone_number}", 
                timeout=15
            )
            print(f"🔍 User state API response: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"🔍 User state data: {data}")
                return data
            else:
                print(f"❌ User state API error: {response.status_code}")
                return {"state": "new", "pending_order": None}
        except Exception as e:
            print(f"❌ Error getting user state: {e}")
            return {"state": "new", "pending_order": None}
    
    def confirm_address(self, phone_number: str, address: str, confirm: bool = True):
        """Confirm or cancel address for pending voice order"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/webhook/confirm-address/{phone_number}",
                json={"address": address, "confirm": confirm},
                timeout=15
            )
            print(f"🔍 Confirm address API response: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"🔍 Confirm address data: {data}")
                return data
            else:
                print(f"❌ Confirm address API error: {response.status_code}")
                return {"status": "error", "message": "Request failed"}
        except Exception as e:
            print(f"❌ Error confirming address: {e}")
            return {"status": "error", "message": str(e)}

def check_voice_service_status():
    """Check and display voice service status"""
    try:
        if hasattr(voice_service, 'asr_pipeline') and voice_service.asr_pipeline:
            return "✅ HuggingFace Wav2Vec2 Model Loaded"
        elif hasattr(voice_service, 'whisper_model') and voice_service.whisper_model:
            return "✅ Whisper Model Loaded"
        else:
            return "🔶 Using Google Speech Recognition"
    except:
        return "🔴 Voice Service Not Available"

def initialize_session_state():
    """Initialize all session state variables"""
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = FoodExpressChatbot()
    
    if 'user_info' not in st.session_state:
        st.session_state.user_info = {
            "name": "Muhammad Ghous",
            "phone": "923002514961", 
            "address": "House No: C 707 Majeed Colony Sector 1 Landhi Karachi",
            "city": "Karachi"
        }
    
    if 'conversations' not in st.session_state:
        st.session_state.conversations = []
    
    if 'orders' not in st.session_state:
        st.session_state.orders = []
    
    if 'menu' not in st.session_state:
        st.session_state.menu = []
    
    if 'show_address_input' not in st.session_state:
        st.session_state.show_address_input = False
    
    if 'pending_order' not in st.session_state:
        st.session_state.pending_order = None
    
    if 'order_completed' not in st.session_state:
        st.session_state.order_completed = False
    
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    if 'backend_connected' not in st.session_state:
        st.session_state.backend_connected = False
    
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "💬 Chat & Order"
    
    if 'connection_retries' not in st.session_state:
        st.session_state.connection_retries = 0
    
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    
    if 'processing_order' not in st.session_state:
        st.session_state.processing_order = False
    
    if 'manual_order_sent' not in st.session_state:
        st.session_state.manual_order_sent = False
    
    # NEW STATE VARIABLES FOR VOICE ORDER CONFIRMATION
    if 'voice_order_pending' not in st.session_state:
        st.session_state.voice_order_pending = False
    
    if 'voice_order_data' not in st.session_state:
        st.session_state.voice_order_data = None
    
    # NEW: Voice processing state
    if 'voice_audio_bytes' not in st.session_state:
        st.session_state.voice_audio_bytes = None
    
    if 'voice_transcription' not in st.session_state:
        st.session_state.voice_transcription = None
    
    if 'voice_order_sent' not in st.session_state:
        st.session_state.voice_order_sent = False

def refresh_data(phone_number: str, force_refresh=False):
    """Refresh all data from backend - FIXED MENU LOADING"""
    try:
        # Only refresh if needed (every 10 seconds minimum)
        current_time = datetime.now()
        time_since_last_refresh = (current_time - st.session_state.last_refresh).seconds
        
        if not force_refresh and time_since_last_refresh < 10 and st.session_state.data_loaded:
            return  # Skip refresh if too soon
        
        # Check backend health first
        health_status = st.session_state.chatbot.check_health()
        st.session_state.backend_connected = health_status
        
        if health_status:
            st.session_state.connection_retries = 0
            
            # Refresh conversations
            conv_data = st.session_state.chatbot.get_conversations(phone_number)
            st.session_state.conversations = conv_data.get('conversations', [])
            
            # Refresh orders
            orders_data = st.session_state.chatbot.get_orders(phone_number)
            st.session_state.orders = orders_data.get('orders', [])
            
            # Refresh menu - FIXED: Handle different response structure
            menu_response = st.session_state.chatbot.get_menu()
            
            # Check different possible response formats
            if isinstance(menu_response, dict):
                if 'menu' in menu_response:
                    # Format 1: {'menu': [...]}
                    st.session_state.menu = menu_response.get('menu', [])
                elif 'menu_by_category' in menu_response:
                    # Format 2: {'menu_by_category': {...}} - flatten it
                    menu_by_category = menu_response.get('menu_by_category', {})
                    flattened_menu = []
                    for category, items in menu_by_category.items():
                        for item in items:
                            flattened_menu.append(item)
                    st.session_state.menu = flattened_menu
                else:
                    # Try to extract menu items from response
                    st.session_state.menu = []
                    for key, value in menu_response.items():
                        if isinstance(value, list):
                            # Check if this list contains menu items
                            if value and isinstance(value[0], dict) and 'name' in value[0] and 'price' in value[0]:
                                st.session_state.menu = value
                                break
            elif isinstance(menu_response, list):
                # If it's already a list
                st.session_state.menu = menu_response
            else:
                st.session_state.menu = []
            
            print(f"✅ Menu loaded: {len(st.session_state.menu)} items")
            
            # NEW: Check for pending voice orders
            print(f"🔄 Checking user state for voice orders...")
            user_state_data = st.session_state.chatbot.get_user_state(phone_number)
            current_state = user_state_data.get('state', 'new')
            pending_order = user_state_data.get('pending_order')
            
            print(f"🔍 Current state: {current_state}, Pending order: {pending_order is not None}")
            
            if current_state == "awaiting_location" and pending_order:
                st.session_state.voice_order_pending = True
                st.session_state.voice_order_data = pending_order
                print(f"🎯 Voice order pending detected!")
            else:
                st.session_state.voice_order_pending = False
                st.session_state.voice_order_data = None
            
            st.session_state.data_loaded = True
        else:
            st.session_state.connection_retries += 1
        
        st.session_state.last_refresh = current_time
        
    except Exception as e:
        st.session_state.backend_connected = False
        print(f"Refresh data error: {e}")

def setup_sidebar():
    """Setup sidebar with user info and quick actions"""
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 20px;'>
            <h2 style='color: white; margin: 0;'>🍕 FoodExpress</h2>
            <p style='color: white; margin: 0; font-size: 12px;'>WhatsApp Food Ordering + Voice</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.header("👤 User Information")
        
        # User inputs
        phone = st.text_input(
            "📱 WhatsApp Number", 
            value=st.session_state.user_info["phone"],
            help="Enter your WhatsApp number with country code (e.g., 923001234567)"
        )
        
        name = st.text_input(
            "👤 Your Name", 
            value=st.session_state.user_info["name"],
            help="Enter your full name for delivery"
        )
        
        city = st.selectbox(
            "🏙️ Your City",
            ["Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar", "Quetta"],
            index=0,
            help="Select your city for delivery"
        )
        
        # Update user info
        st.session_state.user_info.update({
            "phone": phone,
            "name": name,
            "city": city
        })
        
        st.divider()
        
        # Quick actions
        st.header("⚡ Quick Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 Menu", use_container_width=True, help="View complete menu", key="menu_btn"):
                if phone:
                    with st.spinner("Loading menu..."):
                        response = st.session_state.chatbot.send_message("menu", phone)
                        if response.get('status') != 'error':
                            st.success("Menu loaded!")
                            refresh_data(phone, force_refresh=True)
                        else:
                            st.error(f"Failed to load menu: {response.get('message')}")
                else:
                    st.warning("Please enter phone number")
        
        with col2:
            if st.button("📍 Branches", use_container_width=True, help="View branch locations", key="branches_btn"):
                if phone:
                    with st.spinner("Loading branches..."):
                        response = st.session_state.chatbot.send_message("branches", phone)
                        if response.get('status') != 'error':
                            st.success("Branches loaded!")
                            refresh_data(phone, force_refresh=True)
                        else:
                            st.error(f"Failed to load branches: {response.get('message')}")
                else:
                    st.warning("Please enter phone number")
        
        if st.button("🔄 Refresh Data", use_container_width=True, type="secondary", key="refresh_btn"):
            if phone:
                with st.spinner("Refreshing data..."):
                    refresh_data(phone, force_refresh=True)
                    st.success("Data refreshed!")
            else:
                st.warning("Please enter phone number")
        
        st.divider()
        
        # System status
        st.header("📊 System Status")
        
        if st.session_state.backend_connected:
            st.success("✅ Backend Connected")
            # Check voice service status
            voice_status = check_voice_service_status()
            if "✅" in voice_status:
                st.success(f"🎤 {voice_status}")
            elif "🔶" in voice_status:
                st.info(f"🎤 {voice_status}")
            else:
                st.error(f"🎤 {voice_status}")
        else:
            st.error("❌ Backend Not Reachable")
            st.info("Make sure FastAPI server is running on port 8000")
            
        # Connection troubleshooting
        with st.expander("🔧 Troubleshooting"):
            st.write("**If backend is not connecting:**")
            st.write("1. Check if FastAPI server is running")
            st.write("2. Verify port 8000 is available")
            st.write("3. Check terminal for server errors")
            st.write("4. Restart both servers if needed")

def render_voice_order_tab(phone: str):
    """Render the Voice Order tab - IMPROVED VERSION"""
    st.header("🎤 Voice sy Order Karein")
    
    if not st.session_state.backend_connected:
        st.error("🚫 Backend server is not connected. Please make sure the FastAPI server is running on port 8000.")
        return
    
    st.markdown("""
    <div style='background: #E8F5E8; padding: 20px; border-radius: 10px; border: 1px solid #4CAF50; margin-bottom: 20px;'>
        <h3 style='color: #2E7D32; margin-top: 0;'>🎤 Voice sy Order - Aasan Tareeka!</h3>
        <p style='color: #2E7D32; margin-bottom: 0;'>
            Ab ap awaz sy bhi order kar sakte hain! Bas record button dabayein aur apna order bolein.
            <strong>HuggingFace AI technology use ho rahi hai jo ke free hai.</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Voice recording section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🎤 Apna Order Bolein")
        
        # Voice instructions
        with st.expander("📝 Voice Order Instructions (Click here)", expanded=True):
            st.markdown(voice_service.get_voice_instructions())
        
        # Audio recorder - IMPROVED VERSION
        st.write("**Step 1: Apna order record karein (3-10 seconds)**")
        audio_bytes = audio_recorder(
            text="🎤 Record Order",
            recording_color="#e74c3c",
            neutral_color="#3498db",
            icon_name="microphone",
            pause_threshold=3.0,  # 3 seconds minimum
            energy_threshold=0.1  # Lower threshold for better detection
        )
        
        # Store audio bytes in session state
        if audio_bytes:
            st.session_state.voice_audio_bytes = audio_bytes
            st.audio(audio_bytes, format="audio/wav")
            
            # Process audio button
            if st.button("🚀 Process Voice Order", type="primary", key="process_voice", use_container_width=True):
                if st.session_state.voice_audio_bytes:
                    process_voice_audio(phone)
                else:
                    st.error("❌ Please record your order first")
        
        # Show transcription if available
        if st.session_state.voice_transcription:
            st.markdown("---")
            st.subheader("📝 Your Voice Order:")
            st.success(f"**{st.session_state.voice_transcription}**")
            
            # Send to chatbot button
            if not st.session_state.voice_order_sent:
                if st.button("📤 Send Order to Chatbot", type="primary", key="send_voice_order", use_container_width=True):
                    send_voice_order_to_chatbot(phone)
            else:
                st.success("✅ Order sent successfully! Check 'Chat & Order' tab for next steps.")
    
    with col2:
        st.subheader("💡 Tips & Information")
        
        st.markdown("""
        <div style='background: #FFF3CD; padding: 15px; border-radius: 10px; border: 1px solid #FFEAA7;'>
        <h4 style='color: #856404; margin-top: 0;'>✅ Achi Recording ke Liye:</h4>
        <ul style='color: #856404;'>
        <li>Shanti wali jagah use karein</li>
        <li>Mobile mouth se 6 inch door rakhein</li>
        <li>Clear aur slow bolein</li>
        <li>Numbers clear bolein (one, two, three)</li>
        <li>3-10 seconds ki recording best hai</li>
        <li><strong>English mein bolein for better results</strong></li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Technical info
        st.markdown("""
        **🔧 Technology:**
        - HuggingFace Wav2Vec2 AI Model
        - Google Speech Recognition (Backup)
        - Free & Offline Capable
        
        **🌍 Supported Languages:**
        - English (Primary) - Best Results
        - Urdu/Roman Urdu
        - Hindi
        """)
        
        # Quick voice examples
        st.markdown("""
        **🗣️ Voice Order Examples (English):**
        - "Two tea one samosa"
        - "One zinger burger"
        - "Two chicken biryani"
        - "One chocolate cake two mango shake"
        - "Three chai two samosa"
        """)
        
        # Model status
        voice_status = check_voice_service_status()
        if "✅" in voice_status:
            st.success(f"🤖 {voice_status}")
        else:
            st.info(f"🤖 {voice_status}")

def process_voice_audio(phone: str):
    """Process voice audio and transcribe"""
    try:
        with st.spinner("🔮 Awaz process ho rahi hai... AI model use kar raha hai..."):
            # Save audio to temporary file with proper handling
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                temp_audio.write(st.session_state.voice_audio_bytes)
                temp_audio_path = temp_audio.name
            
            try:
                # Process voice order
                transcription = voice_service.process_voice_order(temp_audio_path)
                
                # Clean up - safely delete the file
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)
                
                if transcription and len(transcription) > 5:  # Minimum length check
                    st.session_state.voice_transcription = transcription
                    st.session_state.voice_order_sent = False
                    st.success("✅ Awaz successfully process ho gayi!")
                else:
                    st.error("""
                    ❌ Awaz samajh mein nahi aayi. 
                    
                    **Koshish karein:**
                    - Clear aur slow bolein
                    - Background noise kam karein  
                    - 3-10 seconds ki recording karein
                    - Dobara record karein
                    - English mein bolein: "2 tea 1 samosa"
                    """)
                    
            except Exception as e:
                st.error(f"❌ Voice processing error: {str(e)}")
                st.info("ℹ️ Pehli dafa model load honay mein thora time lag sakta hai.")
    
    except Exception as e:
        st.error(f"❌ Error processing audio: {e}")

def send_voice_order_to_chatbot(phone: str):
    """Send voice transcription to chatbot"""
    if st.session_state.voice_transcription:
        with st.spinner("📤 Order bheja ja raha hai..."):
            response = st.session_state.chatbot.send_message(st.session_state.voice_transcription, phone)
            
            if response.get('status') != 'error':
                st.session_state.voice_order_sent = True
                st.success("🎉 Order successfully bhej diya gaya!")
                
                # Show next steps
                st.markdown("""
                **📍 Ab Next Step:**
                
                1. **Chat & Order** tab mein jayein
                2. Apna delivery address provide karein  
                3. Order confirm karein
                """)
                
                # Force refresh to check for voice order state
                refresh_data(phone, force_refresh=True)
                
                # Auto-switch to chat tab after 2 seconds
                time.sleep(2)
                st.info("🔄 Auto-switching to Chat & Order tab...")
                # Note: We can't automatically switch tabs in Streamlit, but we can show a message
            else:
                st.error(f"❌ Order send karne mein problem: {response.get('message')}")

def show_voice_order_confirmation(phone: str, pending_order):
    """Show address confirmation for pending voice orders - FIXED VERSION"""
    st.success("🎤 **Voice Order Received!**")
    
    # Order details show karein
    st.subheader("📦 Your Voice Order Details:")
    
    # Display order items properly - FIXED: Handle both dict and string
    if pending_order:
        try:
            # Try to parse if it's a string
            if isinstance(pending_order, str):
                try:
                    pending_order = json.loads(pending_order)
                except:
                    # If it's already a JSON string, parse it
                    if pending_order.startswith('{'):
                        pending_order = json.loads(pending_order)
            
            # Now process the order
            if isinstance(pending_order, dict):
                # Try different possible keys for items
                items = None
                if 'items' in pending_order:
                    items = pending_order['items']
                elif 'order_items' in pending_order:
                    items = pending_order['order_items']
                elif 'order' in pending_order:
                    items = pending_order['order']
                
                total = pending_order.get('total_amount', 0) or pending_order.get('total', 0)
                
                if items:
                    if isinstance(items, str):
                        try:
                            items = json.loads(items)
                        except:
                            # If it's a simple string, just display it
                            st.write(f"• **Order:** {items}")
                            items = []
                    
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                item_name = item.get('name', 'Unknown Item') or item.get('item_name', 'Unknown Item')
                                quantity = item.get('quantity', 1) or item.get('qty', 1)
                                price = item.get('price', 0) or item.get('item_price', 0)
                                item_total = quantity * price
                                st.write(f"• **{quantity}x {item_name}** - Rs. {item_total}")
                            else:
                                st.write(f"• {item}")
                    elif isinstance(items, str):
                        st.write(f"• **Order:** {items}")
                    
                    st.write(f"**💰 Total: Rs. {total}**")
                else:
                    # If no items list, show the raw order data
                    st.write("• Order details processing...")
                    if 'order_text' in pending_order:
                        st.write(f"• **Order:** {pending_order['order_text']}")
                    st.write(f"**💰 Total: Rs. {total}**")
            else:
                # If pending_order is not a dict, show it as is
                st.write(f"• **Order:** {pending_order}")
                st.write(f"**💰 Total: Calculating...**")
        except Exception as e:
            st.write(f"• **Order:** Processing...")
            st.write(f"• Error details: {e}")
    
    st.divider()
    st.subheader("📍 Provide Delivery Address")
    
    # Address input with better validation
    user_city = st.session_state.user_info.get('city', 'Karachi')
    address = st.text_area(
        "Enter your complete delivery address:",
        value=f"House #, Street, Area, {user_city}",
        placeholder=f"Example: House No. 123, Street 45, Sector 7, {user_city}",
        height=100,
        key="voice_address_input"
    )
    
    # Special instructions
    instructions = st.text_input(
        "📋 Special Instructions (Optional)",
        placeholder="Any special delivery instructions?",
        key="voice_instructions"
    )
    
    # Action buttons in a row
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("✅ Confirm Order & Address", type="primary", use_container_width=True, key="confirm_voice_order"):
            if address.strip() and address != f"House #, Street, Area, {user_city}":
                # Combine address with instructions if provided
                full_address = address
                if instructions:
                    full_address += f" | instructions: {instructions}"
                
                confirm_voice_order(phone, full_address, pending_order)
            else:
                st.error("❌ Please enter complete delivery address")
    
    with col2:
        if st.button("✏️ Edit Order", use_container_width=True, key="edit_voice_order"):
            st.info("To edit order, cancel this order and place a new one")
    
    with col3:
        if st.button("❌ Cancel Order", use_container_width=True, key="cancel_voice_order"):
            cancel_voice_order(phone)
    
    # Add helpful tips
    st.info("💡 **Tip:** Ensure your address is complete and accurate for timely delivery.")

def confirm_voice_order(phone: str, address: str, pending_order):
    """Confirm voice order with address - FIXED VERSION"""
    try:
        with st.spinner("Confirming your order..."):
            response = st.session_state.chatbot.confirm_address(phone, address, confirm=True)
            
            if response.get('status') in ['confirmed', 'success']:
                st.success("✅ Order confirmed successfully! Delivery address saved.")
                st.balloons()
                
                # Order summary show karein
                st.subheader("📋 Order Summary:")
                st.write(f"**📞 Phone:** {phone}")
                st.write(f"**📍 Address:** {address}")
                st.write(f"**🕐 Estimated Delivery:** 30-45 minutes")
                
                # Reset state
                st.session_state.voice_order_pending = False
                st.session_state.voice_order_data = None
                st.session_state.voice_transcription = None
                st.session_state.voice_audio_bytes = None
                st.session_state.voice_order_sent = False
                
                # Refresh data to update conversations and orders
                refresh_data(phone, force_refresh=True)
                
                # Show success and wait before refreshing
                time.sleep(3)
                st.rerun()
            else:
                error_msg = response.get('message', 'Failed to confirm order')
                st.error(f"❌ {error_msg}")
                
                # Try alternative approach - send as regular message
                st.info("Trying alternative method...")
                alt_response = st.session_state.chatbot.send_message(f"confirm address: {address}", phone)
                if alt_response.get('status') != 'error':
                    st.success("✅ Address sent via alternative method!")
                    st.session_state.voice_order_pending = False
                    st.session_state.voice_order_data = None
                    time.sleep(2)
                    st.rerun()
    except Exception as e:
        st.error(f"❌ Error confirming order: {e}")

def cancel_voice_order(phone: str):
    """Cancel pending voice order"""
    try:
        with st.spinner("Cancelling order..."):
            response = st.session_state.chatbot.confirm_address(phone, "", confirm=False)
            
            if response.get('status') in ['cancelled', 'success']:
                st.info("🗑️ Order cancelled")
                # Reset state
                st.session_state.voice_order_pending = False
                st.session_state.voice_order_data = None
                st.session_state.voice_transcription = None
                st.session_state.voice_audio_bytes = None
                st.session_state.voice_order_sent = False
                
                # Refresh data
                refresh_data(phone, force_refresh=True)
                
                time.sleep(2)
                st.rerun()
            else:
                st.error(f"❌ {response.get('message', 'Failed to cancel order')}")
    except Exception as e:
        st.error(f"❌ Error cancelling order: {e}")

def render_nearby_restaurants_tab(phone: str):
    """Render Nearby Restaurants tab - FIXED VERSION"""
    st.header("📍 Find Nearby Restaurants")
    
    if not st.session_state.backend_connected:
        st.error("🚫 Please connect to backend first")
        return
    
    st.markdown("""
    <div style='background: #E3F2FD; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #1565C0; margin-top: 0;'>🍽️ Discover Restaurants Near You</h3>
        <p style='color: #1565C0; margin-bottom: 0;'>
            Enter your location to find nearby restaurants and food outlets.
            <strong>Using OpenStreetMap - 100% Free!</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Location input
    col1, col2 = st.columns([3, 1])
    
    with col1:
        location_input = st.text_input(
            "Enter your location (Address or Area):",
            placeholder="e.g., Gulshan-e-Iqbal, Karachi or House No. 123, Lahore",
            key="nearby_location_input",
            value="Gulshan-e-Iqbal, Karachi"  # Default value for testing
        )
    
    with col2:
        search_radius = st.selectbox(
            "Search Radius",
            ["2 km", "5 km", "10 km", "20 km"],
            index=1
        )
    
    if st.button("🔍 Search Nearby Restaurants", type="primary", use_container_width=True):
        if location_input:
            with st.spinner("Searching nearby restaurants..."):
                try:
                    # Send location to chatbot for processing
                    location_msg = f"nearby: {location_input} within {search_radius}"
                    response = st.session_state.chatbot.send_message(location_msg, phone)
                    
                    if response.get('status') != 'error':
                        st.success("✅ Searching nearby restaurants...")
                        
                        # Wait a moment for processing
                        time.sleep(1)
                        
                        # Refresh to get updated conversation
                        refresh_data(phone, force_refresh=True)
                        
                        # Show the conversation response
                        if st.session_state.conversations:
                            # Find the latest bot response about restaurants
                            recent_bot_messages = [
                                conv for conv in reversed(st.session_state.conversations[-10:])
                                if conv.get('message_type') == 'bot' and 'restaurant' in conv.get('message_text', '').lower()
                            ]
                            
                            if recent_bot_messages:
                                latest_bot_msg = recent_bot_messages[0]
                                st.markdown(f"**🤖 Bot Response:**")
                                st.info(latest_bot_msg.get('message_text', 'No response found'))
                            else:
                                # Show simulated results as fallback
                                st.info("""
                                **📊 Nearby Restaurants Found:**
                                
                                1. 🏪 **FoodExpress Tariq Road** (1.2 km)
                                   ⭐ 4.3 | ⏰ 25-35 mins | 🍽️ Fast Food, Pakistani
                                
                                2. 🏠 **Cafe Wagera** (0.8 km)
                                   ⭐ 4.1 | ⏰ 15-25 mins | 🍽️ Coffee, Snacks
                                
                                3. 🏪 **FoodExpress Gulshan** (2.3 km)
                                   ⭐ 4.5 | ⏰ 30-40 mins | 🍽️ Pakistani, Grill
                                
                                4. 🏠 **Butt Karahi** (1.5 km)
                                   ⭐ 4.2 | ⏰ 40-50 mins | 🍽️ Pakistani, Karahi
                                
                                5. 🏠 **Pizza Hut** (2.1 km)
                                   ⭐ 4.0 | ⏰ 35-45 mins | 🍽️ Pizza, Italian
                                """)
                        
                        # Map preview
                        st.subheader("🗺️ Location on Map")
                        st.markdown("[View on OpenStreetMap](https://www.openstreetmap.org/)")
                        
                        # Restaurant selection
                        st.subheader("📋 Select a Restaurant")
                        selected = st.radio(
                            "Choose restaurant to order from:",
                            options=["FoodExpress Tariq Road", "Cafe Wagera", "FoodExpress Gulshan", 
                                    "Butt Karahi", "Pizza Hut"],
                            index=0
                        )
                        
                        if st.button("🍽️ Order from Selected Restaurant", type="secondary"):
                            if "FoodExpress" in selected:
                                # Send selection to chatbot
                                st.session_state.chatbot.send_message(f"I want to order from {selected}", phone)
                                st.success(f"✅ Selected: {selected}")
                                st.info("Switching to 'Chat & Order' tab to place your order!")
                                st.session_state.active_tab = "💬 Chat & Order"
                                st.rerun()
                            else:
                                st.warning(f"Note: For ordering from {selected}, please contact them directly. For FoodExpress branches, you can order directly through our system.")
                    
                    else:
                        st.error(f"❌ Error: {response.get('message')}")
                
                except Exception as e:
                    st.error(f"❌ Error searching restaurants: {e}")
        else:
            st.warning("⚠️ Please enter your location")
    
    # Restaurant categories
    st.markdown("---")
    st.subheader("🍽️ Popular Restaurant Categories")
    
    categories = {
        "☕ Coffee & Cafe": ["Cafe Wagera", "Espresso", "Gloria Jean's"],
        "🍔 Fast Food": ["KFC", "McDonald's", "Burger King"],
        "🍛 Pakistani": ["Butt Karahi", "Student Biryani", "Salt'n Pepper"],
        "🍕 Pizza & Italian": ["Pizza Hut", "Domino's", "OPTP"],
        "🥗 Healthy Food": ["Subway", "Saladicious", "Fit & Fresh"]
    }
    
    for category, restaurants in categories.items():
        with st.expander(category):
            for restaurant in restaurants:
                st.write(f"• **{restaurant}**")
    
    # Quick tips
    st.markdown("---")
    st.subheader("💡 Tips for Better Results")
    
    tips = """
    1. **Be specific** with your location (e.g., "Near Dolmen Mall, Karachi")
    2. **Include landmarks** for better accuracy
    3. **Use English** for location names
    4. **Check distance** - closer restaurants deliver faster
    5. **FoodExpress branches** offer fastest delivery
    """
    
    st.info(tips)

def render_chat_order_tab(phone: str):
    """Render the Chat & Order tab - FIXED MENU DISPLAY"""
    st.header("💬 Chat & Order Food")
    
    if not st.session_state.backend_connected:
        st.error("🚫 Backend server is not connected. Please make sure the FastAPI server is running on port 8000.")
        st.info("**To fix this:**")
        st.write("1. Open a terminal/command prompt")
        st.write("2. Navigate to your project directory")
        st.write("3. Run: `python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`")
        st.write("4. Wait for the server to start completely")
        st.write("5. Refresh this page")
        
        if st.button("🔄 Check Connection Again", key="check_conn"):
            refresh_data(phone, force_refresh=True)
        return
    
    # NEW: Check for pending voice orders FIRST
    if st.session_state.voice_order_pending and st.session_state.voice_order_data:
        show_voice_order_confirmation(phone, st.session_state.voice_order_data)
        return  # Skip normal chat flow if voice order pending
    
    # Display menu - FIXED VERSION
    with st.expander("🍽️ Current Menu (Click to expand)", expanded=True):
        if st.session_state.menu and len(st.session_state.menu) > 0:
            # Group by category
            categories = {}
            for item in st.session_state.menu:
                if isinstance(item, dict) and 'name' in item:
                    category = item.get("category", "Other")
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(item)
            
            if categories:
                for category, items in categories.items():
                    if items:
                        st.subheader(f"**{category}**")
                        for item in items:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                item_name = item.get('name', 'Unknown Item')
                                st.write(f"• **{item_name}**")
                                description = item.get('description')
                                if description:
                                    st.caption(f"  {description}")
                            with col2:
                                price = item.get('price', 0)
                                # Format price properly
                                try:
                                    price_float = float(price)
                                    st.write(f"**Rs. {price_float:,.0f}**")
                                except:
                                    st.write(f"**Rs. {price}**")
                        st.write("")
            else:
                st.info("No menu categories found. Menu items may be in incorrect format.")
        else:
            st.info("No menu items available. Click 'Menu' button in sidebar to load.")
    
    # Order completion message
    if st.session_state.order_completed:
        st.success("🎉 **Order Processing Complete!**")
        st.info(f"""
        Your order has been processed successfully!
        
        **Delivery Details:**
        - **City:** {st.session_state.user_info['city']}
        - **Address:** {st.session_state.user_info['address']}
        - **Estimated Delivery:** 30-45 minutes
        
        **Next Steps:**
        1. Check the **Conversations** tab for order summary
        2. Type **'confirm'** to finalize your order
        3. Type **'cancel'** if you want to cancel
        
        You can track your order in the **Orders** tab.
        """)
        
        if st.button("🆕 Place New Order", type="primary", key="new_order"):
            st.session_state.order_completed = False
            st.session_state.show_address_input = False
            st.session_state.pending_order = None
            st.session_state.processing_order = False
            st.session_state.manual_order_sent = False
    
    # Address input section for manual orders
    elif st.session_state.show_address_input and not st.session_state.order_completed:
        st.markdown("---")
        st.subheader("📍 Step 2: Provide Delivery Details")
        
        st.warning("""
        **🚨 IMPORTANT: Delivery Address Required**
        
        Your order has been received! Please provide your complete delivery address to complete the order.
        """)
        
        st.info(f"""
        **Please provide your delivery details:**
        - **City:** {st.session_state.user_info['city']} (selected above)
        - Enter your complete address with area and landmark
        - Example: House No. 123, Street 45, Malir, Near XYZ Hospital, Karachi
        """)
        
        # Address input
        address_input = st.text_area(
            "📝 Complete Delivery Address", 
            value=st.session_state.user_info["address"],
            placeholder=f"Enter your complete delivery address in {st.session_state.user_info['city']}...\nExample: House No. 123, Street 45, Malir, Near XYZ Hospital, Karachi",
            height=100,
            key="address_input"
        )
        
        # Special instructions
        instructions = st.text_input(
            "📋 Special Instructions (Optional)",
            placeholder="Any special delivery instructions?",
            key="delivery_instructions"
        )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            if st.button("✅ Confirm Address & Complete Order", type="primary", use_container_width=True, key="confirm_addr"):
                if address_input.strip():
                    st.session_state.processing_order = True
                    with st.spinner("Completing your order..."):
                        # Update address
                        st.session_state.user_info["address"] = address_input
                        
                        # Send location and address information
                        location_message = f"location: {st.session_state.user_info['city']}, {address_input}"
                        if instructions:
                            location_message += f" | instructions: {instructions}"
                            
                        response = st.session_state.chatbot.send_message(location_message, phone)
                        
                        if response.get('status') != 'error':
                            st.success("✅ Address sent! Processing order...")
                            st.session_state.show_address_input = False
                            st.session_state.order_completed = True
                            st.session_state.processing_order = False
                            refresh_data(phone, force_refresh=True)
                            st.balloons()
                        else:
                            st.error(f"❌ Failed to send address: {response.get('message')}")
                            st.session_state.processing_order = False
                else:
                    st.warning("⚠️ Please enter your delivery address")
        
        with col2:
            if st.button("🔄 Check Status", use_container_width=True, key="check_status"):
                refresh_data(phone, force_refresh=True)
        
        with col3:
            if st.button("❌ Cancel Order", use_container_width=True, key="cancel_addr"):
                cancel_response = st.session_state.chatbot.send_message("cancel", phone)
                st.session_state.show_address_input = False
                st.session_state.pending_order = None
                st.session_state.processing_order = False
                st.session_state.manual_order_sent = False
                st.info("🗑️ Order cancelled")
                refresh_data(phone, force_refresh=True)
        
        st.markdown("---")
    
    # Chat input section (only show if no active order completion)
    elif not st.session_state.order_completed and not st.session_state.processing_order:
        st.subheader("💬 Step 1: Place Your Order")
        
        # Quick order buttons
        st.write("**⚡ Quick Order (Click Once):**")
        col1, col2, col3, col4 = st.columns(4)
        
        quick_orders = [
            ("🍵 Chai Samosa", "2 chai 1 samosa"),
            ("🍔 Zinger Burger", "1 zinger burger"),
            ("🍛 Chicken Biryani", "1 chicken biryani"),
            ("☕ Breakfast", "2 chai 2 samosa")
        ]
        
        for i, (btn_text, order_text) in enumerate(quick_orders):
            with [col1, col2, col3, col4][i]:
                if st.button(btn_text, use_container_width=True, key=f"quick_{i}"):
                    if phone:
                        st.session_state.processing_order = True
                        with st.spinner("Placing order..."):
                            response = st.session_state.chatbot.send_message(order_text, phone)
                            if response.get('status') != 'error':
                                st.success(f"✅ {btn_text} ordered!")
                                # FORCE SHOW ADDRESS INPUT FOR QUICK ORDERS
                                st.session_state.show_address_input = True
                                st.session_state.pending_order = order_text
                                st.session_state.processing_order = False
                                refresh_data(phone, force_refresh=True)
                                st.rerun()  # Force refresh to show address input
                            else:
                                st.error(f"❌ Failed to place order: {response.get('message')}")
                                st.session_state.processing_order = False
                    else:
                        st.warning("⚠️ Please enter phone number first")
        
        # Manual order input
        st.write("**✍️ Type your order manually:**")
        
        # Use form to prevent multiple submissions
        with st.form("order_form", clear_on_submit=True):
            user_message = st.text_input(
                "Type your order here:",
                placeholder=f"Example: 2 chai 1 samosa for delivery in {st.session_state.user_info['city']}",
                key="chat_input"
            )
            
            submitted = st.form_submit_button("📤 Send Order")
            if submitted and user_message and phone:
                st.session_state.processing_order = True
                with st.spinner("Sending order..."):
                    response = st.session_state.chatbot.send_message(user_message, phone)
                    if response.get('status') != 'error':
                        st.success("✅ Order sent!")
                        
                        # ALWAYS SHOW ADDRESS INPUT FOR MANUAL ORDERS
                        st.session_state.show_address_input = True
                        st.session_state.pending_order = user_message
                        st.session_state.manual_order_sent = True
                        
                        st.session_state.processing_order = False
                        refresh_data(phone, force_refresh=True)
                        
                        # Force a rerun to show the address input immediately
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to send order: {response.get('message')}")
                        st.session_state.processing_order = False
        
        # Help section
        with st.expander("🆘 How to Order - Complete Guide"):
            st.markdown(f"""
            **📝 Complete Order Process:**
            
            **Step 1: Place Order**
            - Click quick order buttons OR
            - Type your order manually (e.g., `2 chai 1 samosa`, `1 chicken biryani`)
            
            **Step 2: Provide Address**  
            - System will automatically show address input
            - Enter your complete delivery address
            - Confirm your order
            
            **Step 3: Order Confirmation**
            - Check Conversations tab for order summary
            - Type `confirm` to finalize order
            - Type `cancel` if you want to cancel
            
            **📍 Delivery Information:**
            - **City:** {st.session_state.user_info['city']}
            - **Time:** 30-45 minutes
            - **Minimum Order:** Rs. 300
            
            **💰 All prices in Pakistani Rupees**
            **🚚 Free delivery above Rs. 1000**
            
            **🆘 Troubleshooting:**
            - If address input doesn't appear, refresh the page and try again
            - Make sure your order contains food items and quantities
            - Example: `1 zinger burger 1 coke`
            """)

def render_conversations_tab(phone: str):
    """Render the Conversations tab"""
    st.header("📱 Conversation History")
    
    if not st.session_state.backend_connected:
        st.error("🚫 Backend server is not connected. Please make sure the FastAPI server is running on port 8000.")
        return
    
    if phone:
        # Auto-refresh only if more than 30 seconds passed
        refresh_interval = (datetime.now() - st.session_state.last_refresh).seconds
        if refresh_interval > 30:
            refresh_data(phone)
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write(f"**Phone Number:** `{phone}`")
            st.write(f"**City:** {st.session_state.user_info['city']}")
        with col2:
            st.write(f"**Total Messages:** {len(st.session_state.conversations)}")
        with col3:
            if st.button("🔄 Refresh", use_container_width=True, key="refresh_conv"):
                refresh_data(phone, force_refresh=True)
        
        st.markdown("---")
        
        if st.session_state.conversations:
            # Display conversations in a nice chat interface
            for conv in reversed(st.session_state.conversations[-20:]):  # Show last 20 messages
                message_type = conv.get('message_type', '')
                message_text = conv.get('message_text', '')
                timestamp = conv.get('timestamp', '')
                
                # Format timestamp
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%Y-%m%d %H:%M:%S")
                except:
                    time_str = "Recent"
                
                # Create chat bubbles
                if message_type == 'user':
                    st.markdown(f"""
                    <div style='background: #E3F2FD; padding: 12px; border-radius: 15px; margin: 8px 0; border: 1px solid #BBDEFB; max-width: 80%; margin-left: auto;'>
                        <div style='font-weight: bold; color: #1976D2; font-size: 14px;'>You</div>
                        <div style='color: #333; margin: 5px 0; white-space: pre-wrap;'>{message_text}</div>
                        <div style='font-size: 11px; color: #666; text-align: right;'>{time_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='background: #F5F5F5; padding: 12px; border-radius: 15px; margin: 8px 0; border: 1px solid #E0E0E0; max-width: 80%;'>
                        <div style='font-weight: bold; color: #FF6B35; font-size: 14px;'>FoodExpress 🤖</div>
                        <div style='color: #333; margin: 5px 0; white-space: pre-wrap;'>{message_text}</div>
                        <div style='font-size: 11px; color: #666;'>{time_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Quick action buttons at bottom
            st.markdown("---")
            st.write("**💬 Quick Actions:**")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("✅ Confirm Order", use_container_width=True, key="confirm_quick"):
                    if phone:
                        response = st.session_state.chatbot.send_message("confirm", phone)
                        if response.get('status') != 'error':
                            st.success("Confirmation sent!")
                        else:
                            st.error(f"Failed to confirm: {response.get('message')}")
                        refresh_data(phone, force_refresh=True)
            with col2:
                if st.button("❌ Cancel Order", use_container_width=True, key="cancel_quick"):
                    if phone:
                        response = st.session_state.chatbot.send_message("cancel", phone)
                        if response.get('status') != 'error':
                            st.info("Cancellation sent!")
                        else:
                            st.error(f"Failed to cancel: {response.get('message')}")
                        refresh_data(phone, force_refresh=True)
            with col3:
                if st.button("📍 My Location", use_container_width=True, key="location_quick"):
                    if phone:
                        location_msg = f"location: {st.session_state.user_info['city']}, {st.session_state.user_info['address']}"
                        response = st.session_state.chatbot.send_message(location_msg, phone)
                        if response.get('status') != 'error':
                            st.success("Location sent!")
                        else:
                            st.error(f"Failed to send location: {response.get('message')}")
                        refresh_data(phone, force_refresh=True)
            with col4:
                if st.button("🆘 Help", use_container_width=True, key="help_quick"):
                    if phone:
                        response = st.session_state.chatbot.send_message("help", phone)
                        if response.get('status') != 'error':
                            st.info("Help requested!")
                        else:
                            st.error(f"Failed to get help: {response.get('message')}")
                        refresh_data(phone, force_refresh=True)
        else:
            st.info("""
            💡 **No conversations yet!**
            
            To start chatting:
            1. Go to **Chat & Order** tab
            2. Type a message or use quick order buttons  
            3. Your conversations will appear here
            """)
    else:
        st.warning("""
        ⚠️ **Please enter your WhatsApp number**
        
        1. Go to sidebar on the left  
        2. Enter your WhatsApp number (with country code)
        3. Your conversations will appear here
        """)

def render_orders_tab(phone: str):
    """Render the Orders tab"""
    st.header("📦 Order History")
    
    if not st.session_state.backend_connected:
        st.error("🚫 Backend server is not connected. Please make sure the FastAPI server is running on port 8000.")
        return
    
    if phone:
        if st.button("🔄 Refresh Orders", key="refresh_orders"):
            refresh_data(phone, force_refresh=True)
        
        if st.session_state.orders:
            st.write(f"**Total Orders:** {len(st.session_state.orders)}")
            st.write(f"**Current City:** {st.session_state.user_info['city']}")
            
            for order in st.session_state.orders:
                with st.expander(f"📦 Order #{order['order_id']} - Rs. {order['total_amount']:,.0f} - {order['status'].upper()}", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Status with color coding
                        status = order['status']
                        if status == 'confirmed':
                            st.success(f"**Status:** {status.title()}")
                        elif status == 'pending':
                            st.warning(f"**Status:** {status.title()}")
                        elif status == 'cancelled':
                            st.error(f"**Status:** {status.title()}")
                        elif status == 'delivered':
                            st.info(f"**Status:** {status.title()}")
                        else:
                            st.info(f"**Status:** {status.title()}")
                        
                        st.write(f"**Total:** Rs. {order['total_amount']:,.0f}")
                        if order.get('customer_address'):
                            st.write(f"**Delivery Address:** {order['customer_address']}")
                    
                    with col2:
                        st.write(f"**Branch:** {order.get('branch_name', 'Not assigned')}")
                        st.write(f"**City:** {st.session_state.user_info['city']}")
                        st.write(f"**Date:** {order.get('created_at', 'Unknown')}")
                    
                    if order.get('items'):
                        st.write("**📋 Items Ordered:**")
                        for item in order['items']:
                            st.write(f"• {item['quantity']}x {item['name']} - Rs. {item['total_price']:,.0f}")
                    
                    # Progress bar for order status
                    progress_value = {
                        "pending": 0.2,
                        "confirmed": 0.4, 
                        "preparing": 0.6,
                        "ready": 0.8,
                        "completed": 1.0,
                        "delivered": 1.0
                    }.get(order['status'], 0.1)
                    
                    status_text = f"Order Progress: {order['status'].title()}"
                    if order['status'] == 'delivered':
                        status_text += " 🎉"
                    
                    st.progress(progress_value, text=status_text)
        else:
            st.info("""
            📝 **No orders yet!**
            
            Place your first order:
            1. Go to **Chat & Order** tab  
            2. Select items from menu
            3. Provide delivery address
            4. Confirm your order
            
            Your order history will appear here.
            """)
    else:
        st.warning("⚠️ Please enter your WhatsApp number in sidebar to view orders")

def main():
    # Page configuration
    st.set_page_config(
        page_title="FoodExpress Pakistan - Voice Order",
        page_icon="🎤", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better loading
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.8rem;
        color: #FF6B35;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.3rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #F0F2F6;
        border-radius: 5px 5px 0px 0px;
        gap: 8px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF6B35;
        color: white;
    }
    
    /* Voice recording specific styles */
    .voice-recorder {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
    }
    
    /* Warning boxes */
    .warning-box {
        background-color: #FFF3CD;
        border: 1px solid #FFEAA7;
        border-radius: 5px;
        padding: 16px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    initialize_session_state()
    
    # Show loading while checking connection (only once)
    if not st.session_state.backend_connected and st.session_state.connection_retries == 0:
        refresh_data(st.session_state.user_info["phone"], force_refresh=True)
    
    # Header
    st.markdown('<div class="main-header">🎤 FoodExpress Pakistan - Voice Order</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Awaz sy Order Karein - Bilkul Aasan!</div>', unsafe_allow_html=True)
    
    # Setup sidebar
    setup_sidebar()
    
    # Get phone number from session state
    phone = st.session_state.user_info["phone"]
    
    # Refresh data only once when needed
    if phone and not st.session_state.data_loaded and st.session_state.backend_connected:
        refresh_data(phone, force_refresh=True)
    
    # Main tabs - UPDATED WITH NEARBY RESTAURANTS TAB
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬 Chat & Order", 
        "🎤 Voice Order", 
        "📍 Nearby Restaurants",
        "📱 Conversations", 
        "📦 Orders"
    ])
    
    with tab1:
        render_chat_order_tab(phone)
    
    with tab2:
        render_voice_order_tab(phone)
    
    with tab3:
        render_nearby_restaurants_tab(phone)
    
    with tab4:
        render_conversations_tab(phone)
    
    with tab5:
        render_orders_tab(phone)
    
    # Footer
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write("📞 **Contact:** +92 300 1234567")
    with col2:
        st.write("🎤 **Voice Order Available**")
    with col3:
        st.write("🚚 **30-45 min Delivery**")
    with col4:
        st.write(f"🏙️ **Serving:** {st.session_state.user_info['city']}")

if __name__ == "__main__":
    main()
    