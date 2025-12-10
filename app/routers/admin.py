from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, MenuItem, Branch, Order
from app.models.schemas import MenuItemCreate, BranchCreate

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/menu")
def get_all_menu_items(db: Session = Depends(get_db)):
    """Get all menu items"""
    return db.query(MenuItem).all()

@router.post("/menu")
def add_menu_item(menu_item: MenuItemCreate, db: Session = Depends(get_db)):
    """Add new menu item"""
    db_item = MenuItem(**menu_item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/orders")
def get_all_orders(db: Session = Depends(get_db)):
    """Get all orders"""
    return db.query(Order).all()

@router.get("/branches")
def get_all_branches(db: Session = Depends(get_db)):
    """Get all branches"""
    return db.query(Branch).all()