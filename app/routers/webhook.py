from fastapi import APIRouter, Request, HTTPException, Depends, Body
from sqlalchemy.orm import Session
import json
import logging
import time
from app.models.database import SessionLocal
from app.services.whatsapp_service import WhatsAppService
from app.services.nlp_service import NLPService
from app.services.location_service import LocationService
from app.services.order_service import OrderService
from app.services.voice_service import voice_service

router = APIRouter()
logger = logging.getLogger(__name__)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Verify webhook for WhatsApp API"""
    query_params = dict(request.query_params)
    
    mode = query_params.get("hub.mode")
    token = query_params.get("hub.verify_token")
    challenge = query_params.get("hub.challenge")
    
    verify_token = "foodexpress_pakistan_2024"
    
    if mode and token:
        if mode == "subscribe" and token == verify_token:
            logger.info("✅ WhatsApp webhook verified successfully!")
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Verification failed")
    
    return {"status": "webhook verification endpoint", "verify_token": verify_token}

@router.post("/webhook")
async def webhook_handler(request: Request, db: Session = Depends(get_db)):
    """Handle incoming WhatsApp messages - Now with GREEN-API support"""
    try:
        body = await request.body()
        body_str = body.decode('utf-8')
        
        if not body_str:
            return await handle_demo_message(db)
        
        try:
            webhook_data = json.loads(body_str)
            logger.info(f"📩 Webhook received: {webhook_data}")
            
            # Handle GREEN-API webhook format
            if 'typeWebhook' in webhook_data:
                return await handle_greenapi_webhook(webhook_data, db)
            # Handle Meta webhook format
            elif 'entry' in webhook_data:
                return await handle_meta_webhook(webhook_data, db)
            else:
                return await handle_demo_message(db)
                
        except json.JSONDecodeError:
            return await handle_demo_message(db)
            
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return {"status": "error", "message": str(e)}

async def handle_greenapi_webhook(webhook_data: dict, db: Session):
    """Handle GREEN-API webhook format"""
    webhook_type = webhook_data.get('typeWebhook', '')
    
    if webhook_type == 'incomingMessageReceived':
        message_data = webhook_data.get('messageData', {})
        sender_data = webhook_data.get('senderData', {})
        
        phone_number = sender_data.get('chatId', '').replace('@c.us', '')
        message_type = message_data.get('typeMessage', '')
        
        logger.info(f"📱 GREEN-API: Message from {phone_number}, type: {message_type}")
        
        if message_type == 'textMessage':
            message_text = message_data.get('textMessageData', {}).get('textMessage', '')
            return await process_whatsapp_message({
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": phone_number,
                                "type": "text",
                                "text": {"body": message_text},
                                "timestamp": webhook_data.get('timestamp', '')
                            }]
                        }
                    }]
                }]
            }, db)
        
        elif message_type == 'extendedTextMessage':
            message_text = message_data.get('extendedTextMessageData', {}).get('text', '')
            return await process_whatsapp_message({
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": phone_number,
                                "type": "text", 
                                "text": {"body": message_text},
                                "timestamp": webhook_data.get('timestamp', '')
                            }]
                        }
                    }]
                }]
            }, db)
        
        elif message_type == 'audioMessage':
            # Handle voice messages in GREEN-API
            logger.info(f"🎤 GREEN-API Voice message from {phone_number}")
            return await process_whatsapp_message({
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": phone_number,
                                "type": "audio",
                                "timestamp": webhook_data.get('timestamp', '')
                            }]
                        }
                    }]
                }]
            }, db)
    
    return {"status": "processed", "webhook_type": webhook_type}

async def handle_meta_webhook(webhook_data: dict, db: Session):
    """Handle Meta webhook format"""
    return await process_whatsapp_message(webhook_data, db)

async def handle_demo_message(db: Session):
    """Handle demo message when no webhook data"""
    logger.info("🎯 Running in DEMO MODE - No actual webhook data")
    
    demo_message = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "923001234567",
                        "type": "text",
                        "text": {"body": "hello"},
                        "timestamp": "1700000000"
                    }]
                }
            }]
        }]
    }
    
    return await process_whatsapp_message(demo_message, db)

@router.post("/demo/chat")
async def demo_chat_endpoint(request: Request, db: Session = Depends(get_db)):
    """Demo endpoint to test chat functionality"""
    try:
        body_bytes = await request.body()
        
        if not body_bytes:
            return await process_demo_message("hello", "923001234567", db)
        
        try:
            body = json.loads(body_bytes.decode('utf-8'))
            message = body.get("message", "hello")
            phone_number = body.get("phone_number", "923001234567")
        except json.JSONDecodeError:
            message = "hello"
            phone_number = "923001234567"
        
        return await process_demo_message(message, phone_number, db)
        
    except Exception as e:
        logger.error(f"❌ Error in demo chat: {e}")
        return {"status": "error", "message": str(e)}

async def process_demo_message(message: str, phone_number: str, db: Session):
    """Process demo message"""
    demo_message = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": phone_number,
                        "type": "text", 
                        "text": {"body": message},
                        "timestamp": "1700000000"
                    }]
                }
            }]
        }]
    }
    
    result = await process_whatsapp_message(demo_message, db)
    return {
        "status": "demo_processed", 
        "message": message, 
        "phone_number": phone_number,
        "result": result
    }

async def process_whatsapp_message(message_data, db):
    """Process WhatsApp message - Updated for voice support"""
    whatsapp_service = WhatsAppService()
    nlp_service = NLPService()
    location_service = LocationService()
    order_service = OrderService(db)
    
    try:
        entry = message_data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        
        if not messages:
            return {"status": "no_messages"}
        
        message_data = messages[0]
        user_number = message_data.get("from")
        message_type = message_data.get("type")
        
        logger.info(f"📱 Processing {message_type} from {user_number}")
        
        # Save user message to database
        if message_type == "text":
            message_text = message_data.get("text", {}).get("body", "")
            order_service.save_conversation(user_number, "user", message_text)
        elif message_type == "audio":
            # Handle voice messages
            order_service.save_conversation(user_number, "user", "[Voice Message]")
        
        if message_type == "text":
            await handle_text_message(
                message_data, user_number, whatsapp_service, 
                nlp_service, location_service, order_service
            )
        
        elif message_type == "audio":
            await handle_voice_message(
                message_data, user_number, whatsapp_service, 
                nlp_service, location_service, order_service
            )
        
        elif message_type == "interactive":
            await handle_interactive_message(
                message_data, user_number, whatsapp_service, 
                order_service
            )
    
    except Exception as e:
        logger.error(f"❌ Error processing message: {e}")
        import traceback
        traceback.print_exc()
    
    return {"status": "processed", "user": user_number}

async def handle_voice_message(message_data, user_number, whatsapp_service, nlp_service, location_service, order_service):
    """Handle voice messages from users"""
    try:
        # In real WhatsApp, voice messages would come as audio files
        # For demo, we'll simulate voice processing
        logger.info(f"🎤 Processing voice message from {user_number}")
        
        # For demo purposes, we'll use a simulated voice message
        # In production, you would download the audio file from WhatsApp
        # and process it with voice_service
        
        demo_voice_transcription = "2 cappuccino 1 cookie"  # Simulated transcription
        
        if demo_voice_transcription:
            # Save voice transcription as text message
            order_service.save_conversation(user_number, "user", f"[Voice] {demo_voice_transcription}")
            
            # Process as text message
            simulated_message = {
                "text": {"body": demo_voice_transcription},
                "from": user_number,
                "type": "text"
            }
            
            await handle_text_message(
                simulated_message, user_number, 
                whatsapp_service, nlp_service, location_service, order_service
            )
        else:
            error_msg = "❌ Could not understand voice. Please speak clearly or type your order."
            whatsapp_service.send_text_message(user_number, error_msg)
            order_service.save_conversation(user_number, "bot", error_msg)
            
    except Exception as e:
        logger.error(f"❌ Error processing voice message: {e}")
        error_msg = "❌ Error processing voice. Please try again."
        whatsapp_service.send_text_message(user_number, error_msg)
        order_service.save_conversation(user_number, "bot", error_msg)

async def handle_text_message(message_data, user_number, whatsapp_service, nlp_service, location_service, order_service):
    """Handle text messages from users - UPDATED WITH NEARBY RESTAURANTS & COFFEE SHOP"""
    message_text = message_data.get("text", {}).get("body", "").strip()
    
    logger.info(f"💬 Processing message: '{message_text}' from {user_number}")
    
    user_state = order_service.get_user_state(user_number)
    logger.info(f"🔀 User state: {user_state}")
    
    # Common words that should NOT trigger location detection
    common_words = ["menu", "cancel", "confirm", "order", "help", "hi", "hello", "start", "back", "main", "track"]
    
    # Check if this is a location/address message
    is_explicit_location = (
        message_text.lower().startswith("location:") or 
        message_text.lower().startswith("address:") or
        message_text.lower().startswith("nearby:") or
        any(word in message_text.lower() for word in ["house no", "sector", "colony", "street", "road", "block", "area", "plot no"])
    )
    
    # Determine if this is a location message
    if message_text.lower() in common_words:
        is_location_message = False
    elif user_state == "awaiting_location":
        # When awaiting location, treat most messages as location attempts
        # But exclude common commands
        is_location_message = True
    else:
        is_location_message = is_explicit_location
    
    logger.info(f"📍 Location detection: is_location_message={is_location_message}, explicit={is_explicit_location}")
    
    # Handle restaurant selection (e.g., "1", "2", "3")
    if message_text.isdigit() and user_state == "awaiting_restaurant_choice":
        restaurant_number = int(message_text)
        return await handle_restaurant_selection(
            user_number, restaurant_number, whatsapp_service, location_service, order_service
        )
    
    # Handle location/address input (from Streamlit or WhatsApp)
    if is_location_message:
        logger.info(f"📍 Detected location message: {message_text}")
        
        # Check if it's a nearby search
        if "nearby:" in message_text.lower():
            return await handle_nearby_search(message_text, user_number, whatsapp_service, location_service, order_service)
        
        # Extract address from message
        if "location:" in message_text.lower():
            address = message_text.lower().split("location:")[1].strip()
        elif "address:" in message_text.lower():
            address = message_text.lower().split("address:")[1].strip()
        elif "near me" in message_text.lower() or "around me" in message_text.lower():
            # Extract location from phrases like "coffee near me"
            address = message_text.lower().replace("near me", "").replace("around me", "").replace("coffee", "").replace("restaurant", "").strip()
            if not address:
                address = "current location"
        else:
            address = message_text
        
        # Extract instructions if present
        instructions = None
        if "| instructions:" in address:
            parts = address.split("| instructions:")
            address = parts[0].strip()
            instructions = parts[1].strip() if len(parts) > 1 else None
        
        logger.info(f"📍 Processing address: {address}")
        
        if address and address.lower() != "current location":
            # Convert address to coordinates using LocationService
            lat, lon, formatted_address = location_service.geocode_address(address)
            
            if lat and lon:
                # Get nearby restaurants
                nearby_options = location_service.get_nearby_options(lat, lon)
                
                if nearby_options:
                    # Format restaurant options
                    restaurant_text = location_service.format_nearby_restaurants_text(lat, lon)
                    
                    whatsapp_service.send_text_message(user_number, restaurant_text)
                    order_service.save_conversation(user_number, "bot", restaurant_text)
                    
                    # Update state to wait for restaurant choice
                    order_service.update_user_state(user_number, "awaiting_restaurant_choice")
                    
                    # Save location temporarily
                    order_service.save_temporary_location(user_number, lat, lon, formatted_address)
                    return
                else:
                    # If no restaurants, find nearest branch
                    nearest_branch, distance = location_service.find_nearest_branch(lat, lon)
                    
                    if nearest_branch:
                        return await process_location_with_order(
                            user_number, lat, lon, nearest_branch, distance, 
                            formatted_address, instructions, whatsapp_service, order_service
                        )
                    else:
                        error_msg = "❌ No restaurants found nearby. Please try a different location."
                        whatsapp_service.send_text_message(user_number, error_msg)
                        order_service.save_conversation(user_number, "bot", error_msg)
            else:
                error_msg = "❌ Could not find this location. Please provide a more specific address."
                whatsapp_service.send_text_message(user_number, error_msg)
                order_service.save_conversation(user_number, "bot", error_msg)
        else:
            # Handle "current location" or empty address
            response_msg = "📍 Please share your location using WhatsApp's location feature or type your address."
            whatsapp_service.send_text_message(user_number, response_msg)
            order_service.save_conversation(user_number, "bot", response_msg)
    
    elif user_state == "awaiting_confirmation":
        if "confirm" in message_text.lower():
            order = order_service.confirm_order(user_number)
            if order:
                response_message = f"✅ Order #{order.id} confirmed! Total: Rs. {order.total_amount:,.0f}\nYour order will be ready in 20-25 minutes."
                whatsapp_service.send_text_message(user_number, response_message)
                order_service.save_conversation(user_number, "bot", response_message)
                logger.info(f"✅ Order #{order.id} confirmed for {user_number}")
            else:
                response_message = "❌ No pending order found. Start a new order."
                whatsapp_service.send_text_message(user_number, response_message)
                order_service.save_conversation(user_number, "bot", response_message)
        
        elif "cancel" in message_text.lower():
            order_service.cancel_pending_order(user_number)
            response_message = "❌ Order cancelled. You can start a new order."
            whatsapp_service.send_text_message(user_number, response_message)
            order_service.save_conversation(user_number, "bot", response_message)
        else:
            response_message = "✅ Type 'confirm' to place order\n❌ Type 'cancel' to cancel"
            whatsapp_service.send_text_message(user_number, response_message)
            order_service.save_conversation(user_number, "bot", response_message)
    
    elif user_state == "awaiting_location":
        # Check if it's a common word that should be handled differently
        if message_text.lower() in common_words:
            # Handle common words in awaiting_location state
            if message_text.lower() == "cancel":
                order_service.cancel_pending_order(user_number)
                response_message = "❌ Order cancelled. You can start a new order."
                whatsapp_service.send_text_message(user_number, response_message)
                order_service.save_conversation(user_number, "bot", response_message)
            elif message_text.lower() == "menu":
                menu_items = order_service.get_menu_items()
                menu_message = whatsapp_service.create_menu_list(menu_items)
                whatsapp_service.send_text_message(user_number, menu_message)
                order_service.save_conversation(user_number, "bot", menu_message)
            else:
                # For other common words, send location request
                response_message = whatsapp_service.create_location_request()
                whatsapp_service.send_text_message(user_number, response_message)
                order_service.save_conversation(user_number, "bot", response_message)
        else:
            # Send location request message
            response_message = whatsapp_service.create_location_request()
            whatsapp_service.send_text_message(user_number, response_message)
            order_service.save_conversation(user_number, "bot", response_message)
    
    else:
        # Check if this is NOT a location message before processing as order
        location_keywords = ["location:", "address:", "nearby:", "house no", "sector", "colony", "street", "road", "block", "area"]
        is_potential_location = any(keyword in message_text.lower() for keyword in location_keywords)
        
        if not is_potential_location:
            # IMPROVED CANCEL HANDLING - Check for cancel command first
            if "cancel" in message_text.lower():
                # Check if there's a pending order to cancel
                pending_order = order_service.get_pending_order(user_number)
                if pending_order:
                    order_service.cancel_pending_order(user_number)
                    response_message = "❌ Order cancelled. You can start a new order."
                    whatsapp_service.send_text_message(user_number, response_message)
                    order_service.save_conversation(user_number, "bot", response_message)
                else:
                    # No pending order, show menu
                    menu_items = order_service.get_menu_items()
                    menu_message = whatsapp_service.create_menu_list(menu_items)
                    whatsapp_service.send_text_message(user_number, menu_message)
                    order_service.save_conversation(user_number, "bot", menu_message)
                return  # Exit early after handling cancel
            
            intent = nlp_service.detect_intent(message_text.lower())
            logger.info(f"🎯 Detected intent: {intent}")
            
            # Handle different intents
            if intent == "nearby_restaurants":
                response_msg = "📍 To find nearby restaurants, please share your location or type your address.\nExample: 'coffee near me' or 'location: Gulshan, Karachi'"
                whatsapp_service.send_text_message(user_number, response_msg)
                order_service.save_conversation(user_number, "bot", response_msg)
            
            elif intent == "get_menu":
                menu_items = order_service.get_menu_items()
                menu_message = whatsapp_service.create_menu_list(menu_items)
                whatsapp_service.send_text_message(user_number, menu_message)
                order_service.save_conversation(user_number, "bot", menu_message)
            
            elif intent in ["place_order", "greeting"] or any(word in message_text.lower() for word in ["menu", "order", "coffee", "tea", "food"]):
                menu_items = order_service.get_menu_items()
                
                # Check if this looks like an actual order
                has_numbers = any(char.isdigit() for char in message_text)
                coffee_keywords = ['coffee', 'cappuccino', 'latte', 'espresso', 'americano', 'mocha', 'tea', 'chai', 'juice', 'croissant', 'muffin', 'sandwich', 'salad', 'cake', 'cookie']
                has_coffee_keywords = any(keyword in message_text.lower() for keyword in coffee_keywords)
                
                # Process as order if it has numbers OR coffee keywords
                if has_numbers or has_coffee_keywords:
                    extracted_items = nlp_service.extract_order_items(message_text)
                    
                    if extracted_items:
                        validated_items, invalid_items = nlp_service.validate_menu_items(extracted_items, menu_items)
                        
                        if validated_items:
                            order = order_service.create_temporary_order(user_number, validated_items)
                            
                            if order:
                                # Set user state to awaiting location
                                order_service.update_user_state(user_number, "awaiting_location")
                                
                                # Send location request immediately
                                location_message = whatsapp_service.create_location_request()
                                whatsapp_service.send_text_message(user_number, location_message)
                                order_service.save_conversation(user_number, "bot", location_message)
                                
                                if invalid_items:
                                    invalid_message = f"ℹ️ These items not found: {', '.join(invalid_items)}"
                                    whatsapp_service.send_text_message(user_number, invalid_message)
                                    order_service.save_conversation(user_number, "bot", invalid_message)
                            else:
                                error_message = "❌ Error creating order. Please try again."
                                whatsapp_service.send_text_message(user_number, error_message)
                                order_service.save_conversation(user_number, "bot", error_message)
                        else:
                            # If no items validated, still create a basic order and ask for location
                            if has_numbers:
                                basic_items = [{"item": "custom", "quantity": 1, "price": 200}]
                                order = order_service.create_temporary_order(user_number, basic_items)
                                if order:
                                    order_service.update_user_state(user_number, "awaiting_location")
                                    location_message = whatsapp_service.create_location_request()
                                    whatsapp_service.send_text_message(user_number, location_message)
                                    order_service.save_conversation(user_number, "bot", location_message)
                                
                                invalid_message = "ℹ️ Your order is being processed. Please share your location."
                                whatsapp_service.send_text_message(user_number, invalid_message)
                                order_service.save_conversation(user_number, "bot", invalid_message)
                            else:
                                # Send menu for browsing
                                menu_message = whatsapp_service.create_menu_list(menu_items)
                                whatsapp_service.send_text_message(user_number, menu_message)
                                order_service.save_conversation(user_number, "bot", menu_message)
                    else:
                        # If extraction failed but has numbers, still try to create order
                        if has_numbers:
                            basic_items = [{"item": "custom", "quantity": 1, "price": 200}]
                            order = order_service.create_temporary_order(user_number, basic_items)
                            if order:
                                order_service.update_user_state(user_number, "awaiting_location")
                                location_message = whatsapp_service.create_location_request()
                                whatsapp_service.send_text_message(user_number, location_message)
                                order_service.save_conversation(user_number, "bot", location_message)
                        else:
                            # Send menu for browsing
                            menu_message = whatsapp_service.create_menu_list(menu_items)
                            whatsapp_service.send_text_message(user_number, menu_message)
                            order_service.save_conversation(user_number, "bot", menu_message)
                else:
                    # Send menu for browsing
                    menu_message = whatsapp_service.create_menu_list(menu_items)
                    whatsapp_service.send_text_message(user_number, menu_message)
                    order_service.save_conversation(user_number, "bot", menu_message)
            
            elif intent == "track_order":
                track_message = "📦 To track your order, please provide your order ID.\nExample: 'track order 1'"
                whatsapp_service.send_text_message(user_number, track_message)
                order_service.save_conversation(user_number, "bot", track_message)
            
            elif intent == "branch_info":
                branches_info = order_service.get_branches_info()
                whatsapp_service.send_text_message(user_number, branches_info)
                order_service.save_conversation(user_number, "bot", branches_info)
            
            else:
                welcome_text, buttons = whatsapp_service.create_welcome_message()
                whatsapp_service.send_buttons_message(user_number, welcome_text, buttons)
                order_service.save_conversation(user_number, "bot", welcome_text)
        else:
            # This looks like a location message but user state is not set, ask for order first
            response_message = "❌ Please place an order first, then share your location."
            whatsapp_service.send_text_message(user_number, response_message)
            order_service.save_conversation(user_number, "bot", response_message)

async def handle_restaurant_selection(user_number: str, choice: int, whatsapp_service, location_service, order_service):
    """Handle user's restaurant selection"""
    try:
        # Get saved location
        location_data = order_service.get_temporary_location(user_number)
        
        if not location_data:
            whatsapp_service.send_text_message(
                user_number, 
                "❌ Location not found. Please share your location again."
            )
            return
        
        # Get nearby options again
        nearby_options = location_service.get_nearby_options(
            location_data['lat'], location_data['lon']
        )
        
        if 1 <= choice <= len(nearby_options):
            selected_restaurant = nearby_options[choice - 1]
            
            # If it's our branch
            if selected_restaurant['type'] == 'our_branch':
                # Update order with selected branch
                order_service.update_order_with_branch(
                    user_number, selected_restaurant
                )
                
                # Send order summary
                pending_order = order_service.get_pending_order(user_number)
                if pending_order:
                    order_summary = whatsapp_service.create_order_summary(
                        pending_order['items'],
                        pending_order['total_amount'],
                        selected_restaurant['name'],
                        selected_restaurant['distance_km']
                    )
                    
                    whatsapp_service.send_text_message(user_number, order_summary)
                    order_service.save_conversation(user_number, "bot", order_summary)
                    
                    # Ask for confirmation
                    confirm_msg = "✅ Type 'confirm' to place order\n❌ Type 'cancel' to cancel"
                    whatsapp_service.send_text_message(user_number, confirm_msg)
                    order_service.update_user_state(user_number, "awaiting_confirmation")
                else:
                    whatsapp_service.send_text_message(
                        user_number, 
                        "❌ No pending order found. Please place an order first."
                    )
            
            else:
                # For other restaurants, show menu request option
                whatsapp_service.send_text_message(
                    user_number,
                    f"🍽️ You selected: **{selected_restaurant['name']}**\n"
                    f"📍 {selected_restaurant['distance_km']} km away\n\n"
                    f"Note: For ordering from other restaurants, please contact them directly:\n"
                    f"📞 Phone: {selected_restaurant.get('phone', 'Not available')}\n"
                    f"📍 Address: {selected_restaurant.get('address', 'Not available')}\n\n"
                    f"To order from FoodExpress, please select our branches (🏪)."
                )
                
                order_service.update_user_state(user_number, "new")
        
        else:
            whatsapp_service.send_text_message(
                user_number,
                f"❌ Invalid choice. Please select a number between 1-{len(nearby_options)}"
            )
    
    except Exception as e:
        logger.error(f"❌ Error handling restaurant selection: {e}")
        whatsapp_service.send_text_message(
            user_number, 
            "❌ Error processing selection. Please try again."
        )

async def handle_nearby_search(message_text: str, user_number: str, whatsapp_service, location_service, order_service):
    """Handle nearby restaurant search - FIXED VERSION"""
    try:
        # Extract search query and location
        if "nearby:" in message_text.lower():
            query_parts = message_text.lower().split("nearby:")[1].strip()
        else:
            query_parts = message_text.lower().replace("near me", "").replace("around me", "").strip()
        
        # Parse radius if specified
        radius_km = 5.0  # default radius
        if "within" in query_parts:
            parts = query_parts.split("within")
            if len(parts) >= 2:
                location_part = parts[0].strip()
                radius_part = parts[1].strip().replace("km", "").strip()
                try:
                    radius_km = float(radius_part)
                except ValueError:
                    radius_km = 5.0
            else:
                location_part = query_parts
        else:
            location_part = query_parts
        
        # Clean up location part
        location_part = location_part.strip()
        
        logger.info(f"🔍 Searching nearby for location: {location_part}, radius: {radius_km} km")
        
        # Geocode the address instead of using fixed coordinates
        lat, lon, formatted_address = location_service.geocode_address(location_part)
        
        if lat and lon:
            # Get nearby options using LocationService
            nearby_options = location_service.get_nearby_options(lat, lon)
            
            if nearby_options:
                # Format results
                results_text = f"📍 **RESTAURANTS NEAR {formatted_address}** 📍\n\n"
                
                our_branches = []
                other_restaurants = []
                
                # Separate our branches from other restaurants
                for option in nearby_options[:10]:  # Show up to 10 options
                    if option.get('type') == 'our_branch':
                        our_branches.append(option)
                    else:
                        other_restaurants.append(option)
                
                # Display our branches first
                if our_branches:
                    results_text += "🏪 **FOODEXPRESS BRANCHES** 🏪\n"
                    for i, option in enumerate(our_branches, 1):
                        results_text += f"{i}. **{option['name']}**\n"
                        results_text += f"   📍 {option.get('distance_km', 0):.1f} km | ⭐ {option.get('rating', 4.0)} | ⏰ {option.get('delivery_time', '30-40 mins')}\n"
                        results_text += f"   🍽️ {', '.join(option.get('cuisine', ['Pakistani']))}\n"
                        results_text += f"   📞 {option.get('phone', 'N/A')}\n\n"
                
                # Display other restaurants
                if other_restaurants:
                    results_text += "🏠 **OTHER RESTAURANTS** 🏠\n"
                    start_num = len(our_branches) + 1
                    for i, option in enumerate(other_restaurants, start_num):
                        results_text += f"{i}. **{option['name']}**\n"
                        results_text += f"   📍 {option.get('distance_km', 0):.1f} km | 🍽️ {option.get('cuisine', 'Various')}\n"
                        results_text += f"   🚚 Estimated: {option.get('delivery_time', '40-50 mins')}\n\n"
                
                results_text += "💡 **How to order:**\n"
                results_text += "To order from FoodExpress, select our branches (🏪) by typing the number.\n"
                results_text += "Example: Type '1' to order from FoodExpress Karachi\n\n"
                results_text += "📍 View on map: https://www.openstreetmap.org/"
                
                whatsapp_service.send_text_message(user_number, results_text)
                order_service.save_conversation(user_number, "bot", results_text)
                
                # Update user state to wait for restaurant choice
                order_service.update_user_state(user_number, "awaiting_restaurant_choice")
                
                # Save location temporarily for restaurant selection
                order_service.save_temporary_location(user_number, lat, lon, formatted_address)
                
            else:
                error_msg = f"❌ No restaurants found near '{formatted_address}'. Try a different location."
                whatsapp_service.send_text_message(user_number, error_msg)
                order_service.save_conversation(user_number, "bot", error_msg)
        else:
            error_msg = "❌ Could not find this location. Please provide a valid address."
            whatsapp_service.send_text_message(user_number, error_msg)
            order_service.save_conversation(user_number, "bot", error_msg)
    
    except Exception as e:
        logger.error(f"❌ Error in nearby search: {e}")
        error_msg = "❌ Error searching nearby restaurants. Please try again with a different address."
        whatsapp_service.send_text_message(user_number, error_msg)
        order_service.save_conversation(user_number, "bot", error_msg)

async def process_location_with_order(user_number: str, lat: float, lon: float, nearest_branch: dict, distance: float,
                                    address: str, instructions: str, whatsapp_service, order_service):
    """Process location when there's a pending order"""
    # Get the latest pending order for this user
    pending_order = order_service.get_pending_order(user_number)
    
    if pending_order:
        # Update order with location
        order_data = order_service.update_order_with_location(
            phone_number=user_number, 
            lat=lat, 
            lon=lon, 
            branch_id=nearest_branch['id'],
            address=address,
            instructions=instructions
        )
        
        if order_data:
            order_summary = whatsapp_service.create_order_summary(
                order_data['items'],
                order_data['total_amount'],
                nearest_branch['name'],
                distance
            )
            whatsapp_service.send_text_message(user_number, order_summary)
            order_service.save_conversation(user_number, "bot", order_summary)
            order_service.update_user_state(user_number, "awaiting_confirmation")
            logger.info(f"📍 Address processed: {address}")
            
            # Send confirmation instructions
            confirm_msg = "✅ Type 'confirm' to place order\n❌ Type 'cancel' to cancel"
            whatsapp_service.send_text_message(user_number, confirm_msg)
            order_service.save_conversation(user_number, "bot", confirm_msg)
        else:
            error_msg = "❌ Order update failed. Please try again."
            whatsapp_service.send_text_message(user_number, error_msg)
            order_service.save_conversation(user_number, "bot", error_msg)
    else:
        # No pending order found, ask user to place order first
        error_msg = "❌ No pending order found. Please place an order first."
        whatsapp_service.send_text_message(user_number, error_msg)
        order_service.save_conversation(user_number, "bot", error_msg)

async def handle_interactive_message(message_data, user_number, whatsapp_service, order_service):
    """Handle button clicks from interactive messages"""
    interactive_data = message_data.get("interactive", {})
    button_reply = interactive_data.get("button_reply", {})
    button_id = button_reply.get("id")
    
    logger.info(f"🔘 Button clicked: {button_id}")
    
    if button_id == "order_food":
        menu_items = order_service.get_menu_items()
        menu_message = whatsapp_service.create_menu_list(menu_items)
        whatsapp_service.send_text_message(user_number, menu_message)
        order_service.save_conversation(user_number, "bot", menu_message)
    
    elif button_id == "track_order":
        track_message = "📦 To track your order, please provide your order ID.\nExample: 'track order 1'"
        whatsapp_service.send_text_message(user_number, track_message)
        order_service.save_conversation(user_number, "bot", track_message)
    
    elif button_id == "branch_info":
        branches_info = order_service.get_branches_info()
        whatsapp_service.send_text_message(user_number, branches_info)
        order_service.save_conversation(user_number, "bot", branches_info)
    
    elif button_id == "nearby_restaurants":
        response_msg = "📍 To find nearby restaurants, please share your location or type your address.\nExample: 'coffee near me' or 'location: Gulshan, Karachi'"
        whatsapp_service.send_text_message(user_number, response_msg)
        order_service.save_conversation(user_number, "bot", response_msg)

@router.get("/conversations/{phone_number}")
async def get_conversations(phone_number: str, db: Session = Depends(get_db)):
    """Get conversation history for a phone number"""
    order_service = OrderService(db)
    conversations = order_service.get_conversations(phone_number)
    return {"phone_number": phone_number, "conversations": conversations}

@router.get("/orders/{phone_number}")
async def get_orders(phone_number: str, db: Session = Depends(get_db)):
    """Get order history for a phone number"""
    order_service = OrderService(db)
    orders = order_service.get_orders_by_phone(phone_number)
    return {"phone_number": phone_number, "orders": orders}

@router.get("/whatsapp/health")
async def whatsapp_health_check():
    """Check WhatsApp service health"""
    whatsapp_service = WhatsAppService()
    health_status = whatsapp_service.check_whatsapp_health()
    return health_status

@router.post("/whatsapp/send-test")
async def send_test_message(request: Request):
    """Send test WhatsApp message"""
    try:
        body = await request.json()
        phone_number = body.get("phone_number", "923001234567")
        message = body.get("message", "Test message from FoodExpress Pakistan")
        
        whatsapp_service = WhatsAppService()
        result = whatsapp_service.send_text_message(phone_number, message)
        
        return {
            "status": "success",
            "phone_number": phone_number,
            "result": result
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# =============================================================================
# FIXED ENDPOINTS FOR VOICE ORDER ADDRESS CONFIRMATION
# =============================================================================

@router.get("/webhook/user-state/{phone_number}")
async def get_user_state(phone_number: str, db: Session = Depends(get_db)):
    """Get current user state for frontend"""
    order_service = OrderService(db)
    
    try:
        user_state = order_service.get_user_state(phone_number)
        
        # If user state is awaiting_location, check for pending order too
        pending_order = None
        if user_state == "awaiting_location":
            pending_order = order_service.get_pending_order(phone_number)
            
        return {
            "phone_number": phone_number,
            "state": user_state,
            "pending_order": pending_order
        }
    except Exception as e:
        logger.error(f"❌ Error getting user state: {e}")
        return {"phone_number": phone_number, "state": "new", "pending_order": None}

@router.post("/webhook/confirm-address/{phone_number}")
async def confirm_address(
    phone_number: str,
    request_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Confirm or cancel address for pending order - FIXED FOR VOICE"""
    order_service = OrderService(db)
    whatsapp_service = WhatsAppService()
    
    try:
        # Extract parameters from request body
        address = request_data.get("address", "")
        confirm = request_data.get("confirm", True)
        
        logger.info(f"📍 Confirm address request: phone={phone_number}, address={address[:50]}..., confirm={confirm}")
        
        if confirm:
            # Get pending order
            pending_order = order_service.get_pending_order(phone_number)
            
            if pending_order:
                # Prepare location message
                location_message = f"location: {address}"
                
                # Send location message
                logger.info(f"📍 Sending location message for voice order: {location_message[:50]}...")
                send_result = whatsapp_service.send_text_message(phone_number, location_message)
                
                if send_result:
                    # Wait for processing
                    time.sleep(2)
                    
                    # Get updated user state
                    user_state = order_service.get_user_state(phone_number)
                    logger.info(f"📍 User state after location: {user_state}")
                    
                    if user_state == "awaiting_confirmation":
                        # Send confirmation automatically for voice orders
                        logger.info(f"📍 Auto-confirming order for {phone_number}")
                        confirm_result = whatsapp_service.send_text_message(phone_number, "confirm")
                        
                        if confirm_result:
                            # Wait for confirmation to process
                            time.sleep(1)
                            
                            # Get final state
                            final_state = order_service.get_user_state(phone_number)
                            
                            if final_state == "order_confirmed":
                                return {
                                    "status": "confirmed", 
                                    "message": "Order confirmed successfully!",
                                    "order_id": pending_order.get('id'),
                                    "address": address
                                }
                            else:
                                return {
                                    "status": "awaiting_manual_confirm",
                                    "message": "Order ready for confirmation. Please type 'confirm' in chat.",
                                    "address": address
                                }
                        else:
                            return {
                                "status": "partial", 
                                "message": "Address saved but confirmation failed. Please type 'confirm' in chat.",
                                "address": address
                            }
                    else:
                        return {
                            "status": "address_saved",
                            "message": "Address saved. Please complete order in chat.",
                            "address": address
                        }
                else:
                    return {
                        "status": "error", 
                        "message": "Failed to send location message",
                        "address": address
                    }
            else:
                return {
                    "status": "error", 
                    "message": "No pending order found",
                    "address": address
                }
        else:
            # Cancel order
            order_cancelled = order_service.cancel_pending_order(phone_number)
            if order_cancelled:
                order_service.update_user_state(phone_number, "cancelled")
                return {
                    "status": "cancelled", 
                    "message": "Order cancelled successfully"
                }
            else:
                return {
                    "status": "error", 
                    "message": "No pending order to cancel"
                }
                
    except Exception as e:
        logger.error(f"❌ Error confirming address: {e}")
        return {
            "status": "error", 
            "message": f"Server error: {str(e)}"
        }

# =============================================================================
# VOICE ORDER SPECIFIC ENDPOINTS
# =============================================================================

@router.post("/webhook/process-voice-order/{phone_number}")
async def process_voice_order(
    phone_number: str,
    transcription: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Process voice order transcription"""
    order_service = OrderService(db)
    nlp_service = NLPService()
    
    try:
        logger.info(f"🎤 Processing voice order from {phone_number}: {transcription}")
        
        # Get menu items
        menu_items = order_service.get_menu_items()
        
        # Extract order items from transcription
        extracted_items = nlp_service.extract_order_items(transcription)
        
        if extracted_items:
            validated_items, invalid_items = nlp_service.validate_menu_items(extracted_items, menu_items)
            
            if validated_items:
                # Create temporary order
                order = order_service.create_temporary_order(phone_number, validated_items)
                
                if order:
                    # Set user state to awaiting location
                    order_service.update_user_state(phone_number, "awaiting_location")
                    
                    return {
                        "status": "success",
                        "message": "Voice order processed successfully",
                        "order_id": order.get('id'),
                        "items": validated_items,
                        "invalid_items": invalid_items,
                        "user_state": "awaiting_location"
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Failed to create order"
                    }
            else:
                return {
                    "status": "error",
                    "message": f"No valid items found in: {transcription}",
                    "invalid_items": invalid_items
                }
        else:
            return {
                "status": "error",
                "message": f"Could not extract order items from: {transcription}"
            }
            
    except Exception as e:
        logger.error(f"❌ Error processing voice order: {e}")
        return {
            "status": "error",
            "message": f"Server error: {str(e)}"
        }

@router.get("/webhook/pending-voice-order/{phone_number}")
async def get_pending_voice_order(phone_number: str, db: Session = Depends(get_db)):
    """Get pending voice order details"""
    order_service = OrderService(db)
    
    try:
        # Get user state
        user_state = order_service.get_user_state(phone_number)
        
        # Get pending order
        pending_order = order_service.get_pending_order(phone_number)
        
        # Check if this is a voice order (based on state)
        is_voice_order_pending = (user_state == "awaiting_location" and pending_order is not None)
        
        return {
            "phone_number": phone_number,
            "is_voice_order_pending": is_voice_order_pending,
            "user_state": user_state,
            "pending_order": pending_order
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting pending voice order: {e}")
        return {
            "phone_number": phone_number,
            "is_voice_order_pending": False,
            "user_state": "new",
            "pending_order": None
        }

# =============================================================================
# STREAMLIT SUPPORT ENDPOINTS
# =============================================================================

@router.get("/menu")
async def get_menu_endpoint(db: Session = Depends(get_db)):
    """Get menu items for Streamlit frontend"""
    order_service = OrderService(db)
    menu_items = order_service.get_menu_items()
    return {"menu": menu_items}

@router.get("/health")
async def health_check():
    """Health check endpoint for Streamlit"""
    return {
        "status": "healthy",
        "service": "FoodExpress WhatsApp Bot",
        "timestamp": time.time()
    }