import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

# Constants for data generation
BUSINESS_UNITS = ['SEP01', 'SEP02', 'SEP03', 'SEP04', 'SEP05']
ITEM_CATEGORIES = ['COSMETICS', 'SKINCARE', 'FRAGRANCE', 'HAIRCARE', 'MAKEUP']
STORAGE_TYPES = ['BULK', 'CASE', 'EACH', 'PALLET']
STATUS_CODES = ['Available', 'Hold', 'Damaged', 'Reserved']
ZONES = ['FAST', 'MEDIUM', 'SLOW', 'BULK', 'HAZMAT']

# Helper functions for generating random data
def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)

def random_decimal(min_val: float, max_val: float, decimals: int = 2) -> float:
    return round(random.uniform(min_val, max_val), decimals)

def random_choice(arr: list) -> Any:
    return random.choice(arr)

# Generate Storage Locations
def generate_storage_locations(count: int) -> List[Dict]:
    locations = []
    for i in range(count):
        area = random.randint(1, 5)
        zone = random_choice(ZONES)
        aisle = str(random.randint(1, 50)).zfill(2)
        bay = str(random.randint(1, 100)).zfill(3)
        level = str(random.randint(1, 5)).zfill(2)
        position = str(random.randint(1, 10)).zfill(2)
        
        location_number = f"{area}{aisle}{bay}{level}{position}"
        
        locations.append({
            'location_number': location_number,
            'display_location': location_number,
            'area': str(area),
            'zone': zone,
            'aisle': aisle,
            'bay': bay,
            'level': level,
            'position': position,
            'location_type': random_choice(['RACK', 'FLOOR', 'SHELF']),
            'is_blocked': random.random() < 0.5,
            'created_at': datetime.now().isoformat()
        })
    return locations

# Generate Items
def generate_items(count: int) -> List[Dict]:
    items = []
    for i in range(count):
        item_number = f"ITEM{str(i).zfill(6)}"
        category = random_choice(ITEM_CATEGORIES)
        
        items.append({
            'business_unit': random_choice(BUSINESS_UNITS),
            'item_number': item_number,
            'item_description': f"{category} Product {i}",
            'item_barcode': f"BC{str(i).zfill(8)}",
            'item_category': category,
            'primary_uom': random_choice(['EA', 'CS', 'PL']),
            'abc_classification': random_choice(['A', 'B', 'C']),
            'total_on_hand': random.randint(0, 10000),
            'allocated_quantity': random.randint(0, 1000),
            'standard_cost': random_decimal(1, 1000),
            'created_at': datetime.now().isoformat()
        })
    return items

# Generate LPNs
def generate_lpns(locations: List[Dict], items: List[Dict], count: int) -> List[Dict]:
    lpns = []
    for i in range(count):
        item = random_choice(items)
        location = random_choice(locations)
        
        lpns.append({
            'lpn_number': f"LPN{str(i).zfill(8)}",
            'location_number': location['location_number'],
            'item_number': item['item_number'],
            'quantity': random.randint(1, 100),
            'status': random_choice(STATUS_CODES),
            'facility_status': '3000',
            'created_at': datetime.now().isoformat()
        })
    return lpns

# Generate Location Inventory
def generate_location_inventory(locations: List[Dict], items: List[Dict], count: int) -> List[Dict]:
    inventory = []
    for i in range(count):
        item = random_choice(items)
        location = random_choice(locations)
        
        inventory.append({
            'location_number': location['location_number'],
            'item_number': item['item_number'],
            'current_quantity': random.randint(0, 1000),
            'allocated_quantity': random.randint(0, 100),
            'business_unit': item['business_unit'],
            'created_at': datetime.now().isoformat()
        })
    return inventory

def generate_insert_statements(table_name: str, data: List[Dict]) -> str:
    if not data:
        return ''
    
    columns = ', '.join(data[0].keys())
    values_list = []
    
    for row in data:
        values = []
        for value in row.values():
            if value is None:
                values.append('NULL')
            elif isinstance(value, (str, datetime)):
                values.append(f"'{value}'")
            elif isinstance(value, bool):
                values.append(str(value).lower())
            else:
                values.append(str(value))
        values_list.append(f"({', '.join(values)})")
    
    values_str = ',\n'.join(values_list)
    return f"INSERT INTO {table_name} ({columns})\nVALUES\n{values_str};"

def main():
    # Generate sample data
    locations = generate_storage_locations(1000)
    items = generate_items(500)
    lpns = generate_lpns(locations, items, 2000)
    inventory = generate_location_inventory(locations, items, 1500)
    
    # Generate SQL file content
    sql_content = f"""
-- Storage Locations
{generate_insert_statements('storage_location', locations)}

-- Items
{generate_insert_statements('item_inventory', items)}

-- Location Inventory
{generate_insert_statements('location_inventory', inventory)}

-- LPNs
{generate_insert_statements('lpn_details', lpns)}
"""
    
    # Write to file
    with open('warehouse_data.sql', 'w') as f:
        f.write(sql_content)

if __name__ == '__main__':
    main()