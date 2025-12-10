from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# SQLite Database Configuration
DATABASE_URL = "sqlite:///./whatsapp_food.db"

# SQLite requires check_same_thread=False
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship("Order", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")

class Branch(Base):
    __tablename__ = "branches"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    phone_number = Column(String)
    is_active = Column(Boolean, default=True)
    
    orders = relationship("Order", back_populates="branch")

class MenuItem(Base):
    __tablename__ = "menu_items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    price = Column(Float)
    category = Column(String)
    is_available = Column(Boolean, default=True)
    image_url = Column(String, nullable=True)

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)  # Fixed: added nullable=True
    total_amount = Column(Float)
    status = Column(String, default="pending")
    customer_address = Column(String, nullable=True)  # Fixed: added nullable=True
    customer_latitude = Column(Float, nullable=True)  # Fixed: added nullable=True
    customer_longitude = Column(Float, nullable=True)  # Fixed: added nullable=True
    
    # ADDED MISSING COLUMNS:
    branch_info = Column(Text, nullable=True)  # JSON data for external branches
    user_state = Column(String, default="new")  # Track user conversation state
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="orders")
    branch = relationship("Branch", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")
    
    def __repr__(self):
        return f"<Order(id={self.id}, user_id={self.user_id}, status='{self.status}', total={self.total_amount})>"

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))
    quantity = Column(Integer)
    special_instructions = Column(Text, nullable=True)
    
    order = relationship("Order", back_populates="order_items")
    menu_item = relationship("MenuItem")
    
    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, menu_item_id={self.menu_item_id}, quantity={self.quantity})>"

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message_type = Column(String)  # 'user' or 'bot'
    message_text = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    phone_number = Column(String)
    
    user = relationship("User", back_populates="conversations")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, type='{self.message_type}', text='{self.message_text[:50]}...')>"

# Create tables
Base.metadata.create_all(bind=engine)

print("✅ SQLite Database tables created successfully!")
print("📊 Database Schema Summary:")
print(f"   • User table: 5 columns")
print(f"   • Branch table: 7 columns")
print(f"   • MenuItem table: 7 columns")
print(f"   • Order table: 12 columns (2 new columns added: branch_info, user_state)")
print(f"   • OrderItem table: 6 columns")
print(f"   • Conversation table: 6 columns")