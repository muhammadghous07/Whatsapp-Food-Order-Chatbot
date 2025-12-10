from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class MenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category: str

class MenuItemCreate(MenuItemBase):
    pass

class MenuItem(MenuItemBase):
    id: int
    is_available: bool
    model_config = ConfigDict(from_attributes=True)  # Updated for Pydantic v2

class OrderItemBase(BaseModel):
    menu_item_id: int
    quantity: int
    special_instructions: Optional[str] = None

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: int
    menu_item: MenuItem
    model_config = ConfigDict(from_attributes=True)  # Updated for Pydantic v2

class OrderBase(BaseModel):
    total_amount: float
    status: str

class OrderCreate(OrderBase):
    pass

class Order(OrderBase):
    id: int
    user_id: int
    branch_id: Optional[int]
    created_at: datetime
    order_items: List[OrderItem]
    model_config = ConfigDict(from_attributes=True)  # Updated for Pydantic v2

class BranchBase(BaseModel):
    name: str
    address: str
    latitude: float
    longitude: float
    phone_number: str

class BranchCreate(BranchBase):
    pass

class Branch(BranchBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)  # Updated for Pydantic v2

class UserBase(BaseModel):
    phone_number: str
    name: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)  # Updated for Pydantic v2