from sqlalchemy.orm import Session
from app.models.database import User, Order, OrderItem, MenuItem, Branch, Conversation
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json
import traceback

# Logger setup
logger = logging.getLogger(__name__)

class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.temp_locations = {}  # Temporary location storage for restaurant selection
        self.temp_restaurant_choices = {}  # Temporary restaurant selections
    
    def get_user_state(self, phone_number: str) -> str:
        """Get current conversation state of user from database"""
        try:
            user = self.get_or_create_user(phone_number)
            # Get latest order for this user to check state
            order = self.db.query(Order).filter(
                Order.user_id == user.id
            ).order_by(Order.created_at.desc()).first()
            
            if order and order.user_state:
                return order.user_state
            return "new"
        except Exception as e:
            logger.error(f"❌ Error getting user state from DB: {e}")
            return "new"
    
    def update_user_state(self, phone_number: str, state: str):
        """Update user conversation state in database"""
        try:
            user = self.get_or_create_user(phone_number)
            # Get latest order for this user
            order = self.db.query(Order).filter(
                Order.user_id == user.id
            ).order_by(Order.created_at.desc()).first()
            
            if order:
                order.user_state = state
                self.db.commit()
                logger.info(f"🔀 User {phone_number} state updated in DB to: {state}")
            else:
                logger.warning(f"⚠️ No order found for user {phone_number}, cannot update state")
                
        except Exception as e:
            logger.error(f"❌ Error updating user state in DB: {e}")
    
    def get_or_create_user(self, phone_number: str) -> User:
        """Get existing user or create new one"""
        user = self.db.query(User).filter(User.phone_number == phone_number).first()
        if not user:
            user = User(phone_number=phone_number)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"👤 New user created: {phone_number}")
        return user
    
    def save_conversation(self, phone_number: str, message_type: str, message_text: str):
        """Save conversation to database"""
        try:
            user = self.get_or_create_user(phone_number)
            
            conversation = Conversation(
                user_id=user.id,
                message_type=message_type,
                message_text=message_text,
                phone_number=phone_number,
                timestamp=datetime.utcnow()
            )
            self.db.add(conversation)
            self.db.commit()
            logger.info(f"💬 Conversation saved: {message_type} - {message_text[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ Error saving conversation: {e}")
            self.db.rollback()
    
    def get_conversations(self, phone_number: str, limit: int = 50) -> List[Dict]:
        """Get conversation history for a phone number"""
        try:
            conversations = self.db.query(Conversation).filter(
                Conversation.phone_number == phone_number
            ).order_by(Conversation.timestamp.desc()).limit(limit).all()
            
            return [
                {
                    "id": conv.id,
                    "message_type": conv.message_type,
                    "message_text": conv.message_text,
                    "timestamp": conv.timestamp.isoformat(),
                    "phone_number": conv.phone_number
                }
                for conv in reversed(conversations)  # Reverse to get chronological order
            ]
        except Exception as e:
            logger.error(f"❌ Error getting conversations: {e}")
            return []
    
    def get_orders_by_phone(self, phone_number: str) -> List[Dict]:
        """Get all orders for a phone number"""
        try:
            user = self.get_or_create_user(phone_number)
            orders = self.db.query(Order).filter(Order.user_id == user.id).order_by(Order.created_at.desc()).all()
            
            order_list = []
            for order in orders:
                order_items = []
                for item in order.order_items:
                    order_items.append({
                        'name': item.menu_item.name,
                        'quantity': item.quantity,
                        'price': float(item.menu_item.price),
                        'total_price': float(item.menu_item.price * item.quantity)
                    })
                
                # Get branch info if available
                branch_name = 'Not assigned'
                if order.branch:
                    branch_name = order.branch.name
                elif order.branch_info:
                    # Try to parse from branch_info JSON
                    try:
                        branch_data = json.loads(order.branch_info)
                        branch_name = branch_data.get('name', 'Not assigned')
                    except:
                        pass
                
                order_list.append({
                    'order_id': order.id,
                    'total_amount': float(order.total_amount),
                    'status': order.status,
                    'created_at': order.created_at.isoformat(),
                    'branch_name': branch_name,
                    'customer_address': order.customer_address,
                    'items': order_items
                })
            
            return order_list
        except Exception as e:
            logger.error(f"❌ Error getting orders: {e}")
            return []
    
    def get_menu_items(self) -> List[Dict]:
        """Get all available menu items - FILTERED"""
        items = self.db.query(MenuItem).filter(
            MenuItem.is_available == True,
            MenuItem.name != 'string',
            MenuItem.price > 0
        ).all()
        
        menu_list = [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "price": float(item.price),
                "category": item.category
            }
            for item in items
        ]
        logger.info(f"📋 Retrieved {len(menu_list)} valid menu items")
        return menu_list
    
    def create_temporary_order(self, phone_number: str, items: List[Dict]) -> Optional[Order]:
        """Create a temporary order - FIXED VERSION"""
        try:
            user = self.get_or_create_user(phone_number)
            
            # Calculate total - CORRECTED CALCULATION
            total = 0
            valid_items = []
            
            for item in items:
                menu_item_id = item.get('menu_item_id')
                quantity = item.get('quantity', 1)
                
                if not menu_item_id:
                    continue
                
                # Get menu item from database to get actual price
                menu_item = self.db.query(MenuItem).filter(
                    MenuItem.id == menu_item_id
                ).first()
                
                if menu_item:
                    item_total = float(menu_item.price) * quantity
                    total += item_total
                    valid_items.append({
                        'menu_item_id': menu_item_id,
                        'quantity': quantity,
                        'price': float(menu_item.price),
                        'total_price': item_total
                    })
                else:
                    logger.warning(f"Menu item with id {menu_item_id} not found, skipping")
            
            if total <= 0:
                total = 500  # Default minimum amount
            
            # Create order
            order = Order(
                user_id=user.id,
                total_amount=total,
                status="draft",
                user_state="awaiting_location"  # Set state directly
            )
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)
            
            # Add order items
            for item in valid_items:
                order_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=item['menu_item_id'],
                    quantity=item['quantity']
                )
                self.db.add(order_item)
            
            self.db.commit()
            
            logger.info(f"🛒 Temporary order created: #{order.id} for {phone_number}, Total: Rs. {total}")
            return order
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error creating temporary order: {e}")
            traceback.print_exc()
            return None
    
    def update_order_with_location(self, phone_number: str, lat: float, lon: float, 
                                 branch_id: Optional[int] = None, branch_data: Optional[Dict] = None,
                                 address: str = None, instructions: str = None) -> Optional[Dict]:
        """Update order with location and branch information - UPDATED"""
        try:
            user = self.get_or_create_user(phone_number)
            
            # Get latest draft order
            order = self.db.query(Order).filter(
                Order.user_id == user.id,
                Order.status == "draft"
            ).order_by(Order.created_at.desc()).first()
            
            if order:
                order.customer_latitude = lat
                order.customer_longitude = lon
                
                if branch_id:
                    order.branch_id = branch_id
                
                if branch_data:
                    # Store branch data as JSON if not in our database
                    order.branch_info = json.dumps(branch_data)
                
                if address:
                    order.customer_address = address
                
                # Update user state in database
                order.user_state = "awaiting_confirmation"
                
                self.db.commit()
                
                # Get order items for summary
                items = []
                for order_item in order.order_items:
                    items.append({
                        'name': order_item.menu_item.name,
                        'quantity': order_item.quantity,
                        'price': float(order_item.menu_item.price),
                        'total_price': float(order_item.menu_item.price * order_item.quantity)
                    })
                
                # Get branch name
                branch_name = None
                if order.branch:
                    branch_name = order.branch.name
                elif order.branch_info:
                    try:
                        branch_data_json = json.loads(order.branch_info)
                        branch_name = branch_data_json.get('name')
                    except:
                        pass
                
                order_data = {
                    'id': order.id,
                    'items': items,
                    'total_amount': float(order.total_amount),
                    'customer_address': order.customer_address,
                    'customer_lat': order.customer_latitude,
                    'customer_lon': order.customer_longitude,
                    'branch_id': order.branch_id,
                    'branch_name': branch_name,
                    'user_state': order.user_state
                }
                
                logger.info(f"📍 Order #{order.id} updated with location, state: {order.user_state}")
                return order_data
            
            return None
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error updating order with location: {e}")
            return None
    
    def confirm_order(self, phone_number: str) -> Optional[Order]:
        """Confirm the order and change status to confirmed"""
        try:
            user = self.get_or_create_user(phone_number)
            
            order = self.db.query(Order).filter(
                Order.user_id == user.id,
                Order.status == "draft"
            ).order_by(Order.created_at.desc()).first()
            
            if order:
                order.status = "confirmed"
                order.created_at = datetime.utcnow()  # Set actual confirmation time
                order.user_state = "new"  # Reset state
                self.db.commit()
                
                # Clear temporary data
                self.clear_temporary_data(phone_number)
                
                logger.info(f"✅ Order #{order.id} confirmed successfully, state reset to: {order.user_state}")
                return order
            
            return None
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error confirming order: {e}")
            return None
    
    def cancel_pending_order(self, phone_number: str) -> bool:
        """Cancel pending order"""
        try:
            user = self.get_or_create_user(phone_number)
            
            order = self.db.query(Order).filter(
                Order.user_id == user.id,
                Order.status == "draft"
            ).order_by(Order.created_at.desc()).first()
            
            if order:
                order.status = "cancelled"
                order.user_state = "new"  # Reset state
                self.db.commit()
                logger.info(f"❌ Order #{order.id} cancelled, state reset to: {order.user_state}")
                
                # Clear temporary data
                self.clear_temporary_data(phone_number)
                
                return True
            
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error cancelling order: {e}")
            return False
    
    def get_branches_info(self) -> str:
        """Get formatted branches information"""
        branches = self.db.query(Branch).filter(Branch.is_active == True).all()
        
        if not branches:
            return "❌ No branches available at the moment."
        
        branches_text = "📍 **OUR BRANCHES** 📍\n\n"
        for branch in branches:
            branches_text += f"**{branch.name}**\n"
            branches_text += f"🏠 {branch.address}\n"
            branches_text += f"📞 {branch.phone_number}\n\n"
        
        return branches_text
    
    def get_order_status(self, phone_number: str, order_id: int) -> Optional[str]:
        """Get status of specific order"""
        user = self.get_or_create_user(phone_number)
        
        order = self.db.query(Order).filter(
            Order.user_id == user.id,
            Order.id == order_id
        ).first()
        
        return order.status if order else None
    
    def get_branches(self) -> List[Dict]:
        """Get all active branches"""
        branches = self.db.query(Branch).filter(Branch.is_active == True).all()
        return [
            {
                "id": branch.id,
                "name": branch.name,
                "address": branch.address,
                "latitude": float(branch.latitude) if branch.latitude else None,
                "longitude": float(branch.longitude) if branch.longitude else None,
                "phone_number": branch.phone_number
            }
            for branch in branches
        ]

    def get_pending_order(self, phone_number: str) -> Optional[Dict]:
        """Get the latest pending order for a user"""
        try:
            user = self.get_or_create_user(phone_number)
            
            # Get the latest order for this user with draft status
            order = self.db.query(Order).filter(
                Order.user_id == user.id,
                Order.status == 'draft'
            ).order_by(Order.created_at.desc()).first()
            
            if order:
                # Get order items
                order_items = self.db.query(OrderItem).filter(
                    OrderItem.order_id == order.id
                ).all()
                
                # Convert to dictionary format
                items_list = []
                for item in order_items:
                    menu_item = self.db.query(MenuItem).filter(
                        MenuItem.id == item.menu_item_id
                    ).first()
                    
                    if menu_item:
                        items_list.append({
                            'name': menu_item.name,
                            'quantity': item.quantity,
                            'price': float(menu_item.price),
                            'total_price': float(menu_item.price * item.quantity)
                        })
                
                # Get branch info
                branch_name = None
                if order.branch:
                    branch_name = order.branch.name
                elif order.branch_info:
                    try:
                        branch_data = json.loads(order.branch_info)
                        branch_name = branch_data.get('name')
                    except:
                        pass
                
                order_dict = {
                    'id': order.id,
                    'customer_phone': phone_number,
                    'total_amount': float(order.total_amount),
                    'status': order.status,
                    'branch_id': order.branch_id,
                    'branch_name': branch_name,
                    'customer_address': order.customer_address,
                    'customer_lat': float(order.customer_latitude) if order.customer_latitude else None,
                    'customer_lon': float(order.customer_longitude) if order.customer_longitude else None,
                    'user_state': order.user_state,
                    'items': items_list,
                    'created_at': order.created_at.isoformat() if order.created_at else None
                }
                
                return order_dict
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting pending order: {e}")
            return None

    # NEW METHODS FOR RESTAURANT SELECTION AND LOCATION MANAGEMENT
    
    def save_temporary_location(self, phone_number: str, lat: float, lon: float, address: str):
        """Save location temporarily for restaurant selection"""
        self.temp_locations[phone_number] = {
            'lat': lat,
            'lon': lon,
            'address': address,
            'timestamp': datetime.utcnow()
        }
        logger.info(f"📍 Saved temporary location for {phone_number}: {lat}, {lon}")
    
    def get_temporary_location(self, phone_number: str) -> Optional[Dict]:
        """Get saved temporary location"""
        location = self.temp_locations.get(phone_number)
        if location:
            # Check if location is still valid (less than 30 minutes old)
            time_diff = datetime.utcnow() - location['timestamp']
            if time_diff.total_seconds() < 1800:  # 30 minutes
                return location
            else:
                # Remove expired location
                del self.temp_locations[phone_number]
        return None
    
    def save_restaurant_choice(self, phone_number: str, restaurant_data: Dict):
        """Save user's restaurant choice temporarily"""
        self.temp_restaurant_choices[phone_number] = restaurant_data
        logger.info(f"🍽️ Saved restaurant choice for {phone_number}: {restaurant_data.get('name')}")
    
    def get_restaurant_choice(self, phone_number: str) -> Optional[Dict]:
        """Get saved restaurant choice"""
        return self.temp_restaurant_choices.get(phone_number)
    
    def update_order_with_branch(self, phone_number: str, branch_data: Dict) -> bool:
        """Update order with selected branch"""
        try:
            user = self.get_or_create_user(phone_number)
            
            # Get latest draft order
            order = self.db.query(Order).filter(
                Order.user_id == user.id,
                Order.status == "draft"
            ).order_by(Order.created_at.desc()).first()
            
            if order:
                # Check if this is one of our branches
                branch = None
                if branch_data.get('type') == 'our_branch':
                    # Try to find in database
                    branch = self.db.query(Branch).filter(
                        Branch.name.ilike(f"%{branch_data['name']}%")
                    ).first()
                
                if branch:
                    order.branch_id = branch.id
                else:
                    # Store branch data as JSON
                    order.branch_info = json.dumps(branch_data)
                
                # If we have temporary location, update order with it
                temp_location = self.get_temporary_location(phone_number)
                if temp_location:
                    order.customer_latitude = temp_location['lat']
                    order.customer_longitude = temp_location['lon']
                    order.customer_address = temp_location['address']
                
                # Update user state
                order.user_state = "awaiting_confirmation"
                
                self.db.commit()
                
                # Save restaurant choice for later use
                self.save_restaurant_choice(phone_number, branch_data)
                
                logger.info(f"✅ Order #{order.id} updated with branch: {branch_data.get('name')}, state: {order.user_state}")
                return True
            
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error updating order with branch: {e}")
            return False
    
    def update_order_with_address(self, phone_number: str, address: str) -> Optional[Order]:
        """Update pending order with address"""
        try:
            user = self.get_or_create_user(phone_number)
            
            # Get the latest draft order
            order = self.db.query(Order).filter(
                Order.user_id == user.id,
                Order.status == 'draft'
            ).order_by(Order.created_at.desc()).first()
            
            if order:
                # Update order with address
                order.customer_address = address
                self.db.commit()
                self.db.refresh(order)
                logger.info(f"📍 Order #{order.id} updated with address: {address}")
                return order
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error updating order with address: {e}")
            return None
    
    def clear_temporary_data(self, phone_number: str):
        """Clear temporary stored data"""
        if phone_number in self.temp_locations:
            del self.temp_locations[phone_number]
            logger.info(f"🗑️ Cleared temporary location for {phone_number}")
        
        if phone_number in self.temp_restaurant_choices:
            del self.temp_restaurant_choices[phone_number]
            logger.info(f"🗑️ Cleared restaurant choice for {phone_number}")
    
    def get_pending_order_for_user(self, phone_number: str) -> Optional[Dict]:
        """Get pending order for user - ALIAS METHOD FOR COMPATIBILITY"""
        return self.get_pending_order(phone_number)
    
    def get_available_branches_near_location(self, lat: float, lon: float, max_distance_km: float = 50.0) -> List[Dict]:
        """Get branches near a location"""
        try:
            from haversine import haversine
            
            branches = self.get_branches()
            nearby_branches = []
            
            for branch in branches:
                if branch['latitude'] is None or branch['longitude'] is None:
                    continue
                    
                branch_coords = (branch['latitude'], branch['longitude'])
                user_coords = (lat, lon)
                
                distance = haversine(user_coords, branch_coords)
                
                if distance <= max_distance_km:
                    branch_with_distance = branch.copy()
                    branch_with_distance['distance_km'] = round(distance, 2)
                    branch_with_distance['type'] = 'our_branch'
                    nearby_branches.append(branch_with_distance)
            
            # Sort by distance
            nearby_branches.sort(key=lambda x: x['distance_km'])
            return nearby_branches
            
        except ImportError:
            logger.warning("haversine package not installed. Please install it: pip install haversine")
            return []
        except Exception as e:
            logger.error(f"❌ Error getting nearby branches: {e}")
            return []
    
    def create_order_summary(self, order_data: Dict) -> str:
        """Create formatted order summary text"""
        if not order_data:
            return "No order data available."
        
        items_text = "\n".join([
            f"• {item['quantity']}x {item['name']} - Rs. {item['total_price']:,.0f}" 
            for item in order_data.get('items', [])
        ])
        
        total = order_data.get('total_amount', 0)
        branch_name = order_data.get('branch_name', 'Not assigned')
        address = order_data.get('customer_address', 'Not provided')
        
        summary = f"""📋 **ORDER SUMMARY**

{items_text}

────────────────
💰 **Total Amount: Rs. {total:,.0f}**
📍 **Branch: {branch_name}**
🏠 **Address: {address}**

✅ Type 'confirm' to place order
❌ Type 'cancel' to cancel"""

        return summary
    
    def get_user_order_history(self, phone_number: str, limit: int = 10) -> List[Dict]:
        """Get user's order history with details"""
        try:
            user = self.get_or_create_user(phone_number)
            orders = self.db.query(Order).filter(
                Order.user_id == user.id,
                Order.status.in_(["confirmed", "completed", "delivered"])
            ).order_by(Order.created_at.desc()).limit(limit).all()
            
            history = []
            for order in orders:
                # Get order items
                items = []
                for order_item in order.order_items:
                    items.append({
                        'name': order_item.menu_item.name,
                        'quantity': order_item.quantity,
                        'price': float(order_item.menu_item.price),
                        'total_price': float(order_item.menu_item.price * order_item.quantity)
                    })
                
                # Get branch info
                branch_name = None
                if order.branch:
                    branch_name = order.branch.name
                elif order.branch_info:
                    try:
                        branch_data = json.loads(order.branch_info)
                        branch_name = branch_data.get('name')
                    except:
                        pass
                
                history.append({
                    'order_id': order.id,
                    'total_amount': float(order.total_amount),
                    'status': order.status,
                    'branch_name': branch_name,
                    'customer_address': order.customer_address,
                    'items': items,
                    'created_at': order.created_at.isoformat() if order.created_at else None
                })
            
            return history
            
        except Exception as e:
            logger.error(f"❌ Error getting order history: {e}")
            return []
    
    def search_menu_items(self, query: str, category: str = None) -> List[Dict]:
        """Search menu items by query and optional category"""
        try:
            query_filter = MenuItem.name.ilike(f"%{query}%") | MenuItem.description.ilike(f"%{query}%")
            
            if category:
                items = self.db.query(MenuItem).filter(
                    MenuItem.is_available == True,
                    MenuItem.category == category,
                    query_filter
                ).all()
            else:
                items = self.db.query(MenuItem).filter(
                    MenuItem.is_available == True,
                    query_filter
                ).all()
            
            return [
                {
                    "id": item.id,
                    "name": item.name,
                    "description": item.description,
                    "price": float(item.price),
                    "category": item.category
                }
                for item in items
            ]
            
        except Exception as e:
            logger.error(f"❌ Error searching menu items: {e}")
            return []
    
    def get_menu_categories(self) -> List[str]:
        """Get all menu categories"""
        try:
            categories = self.db.query(MenuItem.category).distinct().all()
            return [cat[0] for cat in categories if cat[0]]
        except Exception as e:
            logger.error(f"❌ Error getting menu categories: {e}")
            return []
    
    def update_order_status(self, order_id: int, status: str) -> bool:
        """Update order status"""
        try:
            order = self.db.query(Order).filter(Order.id == order_id).first()
            if order:
                order.status = status
                self.db.commit()
                logger.info(f"🔄 Order #{order_id} status updated to: {status}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error updating order status: {e}")
            return False
    
    def update_order_with_instructions(self, phone_number: str, instructions: str) -> bool:
        """Update order with special instructions"""
        try:
            user = self.get_or_create_user(phone_number)
            
            order = self.db.query(Order).filter(
                Order.user_id == user.id,
                Order.status == "draft"
            ).order_by(Order.created_at.desc()).first()
            
            if order:
                order.special_instructions = instructions
                self.db.commit()
                logger.info(f"📝 Order #{order.id} updated with instructions")
                return True
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error updating order instructions: {e}")
            return False
    
    def get_active_order_count(self, phone_number: str) -> int:
        """Get count of active (draft) orders for user"""
        try:
            user = self.get_or_create_user(phone_number)
            count = self.db.query(Order).filter(
                Order.user_id == user.id,
                Order.status == "draft"
            ).count()
            return count
        except Exception as e:
            logger.error(f"❌ Error getting active order count: {e}")
            return 0
    
    def validate_order_items(self, items: List[Dict]) -> Dict[str, Any]:
        """Validate order items before creating order"""
        try:
            validated_items = []
            total = 0
            
            for item in items:
                menu_item_id = item.get('menu_item_id')
                quantity = item.get('quantity', 1)
                
                if not menu_item_id or quantity <= 0:
                    continue
                
                menu_item = self.db.query(MenuItem).filter(
                    MenuItem.id == menu_item_id,
                    MenuItem.is_available == True
                ).first()
                
                if menu_item:
                    item_total = float(menu_item.price) * quantity
                    total += item_total
                    validated_items.append({
                        'menu_item_id': menu_item_id,
                        'quantity': quantity,
                        'price': float(menu_item.price),
                        'total_price': item_total,
                        'name': menu_item.name
                    })
            
            return {
                'valid': len(validated_items) > 0,
                'items': validated_items,
                'total': total,
                'message': f"Validated {len(validated_items)} items with total Rs. {total:,.0f}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error validating order items: {e}")
            return {
                'valid': False,
                'items': [],
                'total': 0,
                'message': f"Validation error: {str(e)}"
            }