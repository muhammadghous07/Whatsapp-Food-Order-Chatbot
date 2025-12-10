import json
import os
from typing import Any, Dict

def load_json_file(file_path: str, default_data: Any = None) -> Any:
    """Load JSON file with default fallback"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        if default_data is not None:
            save_json_file(file_path, default_data)
            return default_data
        return None

def save_json_file(file_path: str, data: Any):
    """Save data to JSON file"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def format_currency(amount: float) -> str:
    """Format amount as currency"""
    return f"${amount:.2f}"

def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    import re
    # Basic international phone validation
    pattern = r'^\+?[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone))

def get_distance_text(distance_km: float) -> str:
    """Format distance in readable text"""
    if distance_km < 1:
        return f"{distance_km * 1000:.0f} meters"
    else:
        return f"{distance_km:.1f} km"