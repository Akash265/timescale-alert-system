import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from faker import Faker
import psycopg2
import pytz

fake = Faker()

# Constants
BUSINESS_UNITS = ['SEP01', 'SEP02', 'SEP03', 'SEP04', 'SEP05']
PRIORITIES = ['HIGH', 'MEDIUM', 'LOW', 'RUSH']
ORDER_TYPES = ['SO', 'TO', 'RMA']
PIPELINES = ['ECOMM', 'WHOLESALE', 'RETAIL', 'RETURN']
PLANNING_TYPES = ['WAVE', 'DYNAMIC', 'BATCH']
ORDER_STATUS = ['CREATED', 'RELEASED', 'PICKED', 'PACKED', 'SHIPPED', 'DELIVERED']
PLANNING_MODES = ['NORMAL', 'EXPEDITED', 'CONSOLIDATED']
PIPELINE_STATUS = ['NEW', 'ALLOCATED', 'PICKED', 'PACKED', 'SHIPPED']
SHIP_VIAS = ['UPS_GROUND', 'FEDEX_GROUND', 'FEDEX_AIR', 'UPS_AIR']
FACILITIES = ['DC1', 'DC2', 'DC3', 'DC4']
ITEM_PREFIX = 'ITEM'
US_STATES = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
]

# Database connection details
CONNECTION = "postgres://tsdbadmin:m362xngx89whn28r@rmjil6bz1d.hlsqzxo5q3.tsdb.cloud.timescale.com:39236/tsdb?sslmode=require"

def generate_address() -> Dict[str, str]:
    """Generate a random US address."""
    return {
        'address_line1': fake.street_address(),
        'address_line2': fake.secondary_address() if random.random() < 0.3 else None,
        'city': fake.city(),
        'state': random.choice(US_STATES),
        'postal_code': fake.zipcode(),
        'country': 'USA'
    }

def random_datetime(start_date: datetime, end_date: datetime) -> datetime:
    """Generate a random datetime between start and end date."""
    return fake.date_time_between(start_date=start_date, end_date=end_date, tzinfo=pytz.UTC)

def random_future_datetime(start_date: datetime, max_days: int = 30) -> datetime:
    """Generate a random future datetime."""
    end_date = start_date + timedelta(days=max_days)
    return random_datetime(start_date, end_date)

def generate_dc_orders(count: int, start_date: datetime = None) -> List[Dict]:
    """Generate DC orders data."""
    if start_date is None:
        start_date = datetime.now(pytz.UTC)

    orders = []
    for i in range(count):
        order_number = f"ORD{str(i*100 + 1).zfill(8)}"
        business_unit = random.choice(BUSINESS_UNITS)
        
        # Generate order timestamps
        order_placed = random_datetime(
            start_date - timedelta(days=7),
            start_date
        )
        pickup_start = random_future_datetime(order_placed, 3)
        pickup_end = pickup_start + timedelta(hours=random.randint(2, 8))
        delivery_start = pickup_end + timedelta(days=random.randint(1, 5))
        delivery_end = delivery_start + timedelta(hours=random.randint(4, 12))

        # Generate addresses
        origin = generate_address()
        destination = generate_address()

        orders.append({
            'business_unit': business_unit,
            'order_number': order_number,
            'priority': random.choice(PRIORITIES),
            'maximum_status': random.choice(ORDER_STATUS),
            'order_type': random.choice(ORDER_TYPES),
            'pipeline': random.choice(PIPELINES),
            'origin_facility': random.choice(FACILITIES),
            'origin_address_line1': origin['address_line1'],
            'origin_address_line2': origin['address_line2'],
            'origin_city': origin['city'],
            'origin_state': origin['state'],
            'origin_postal_code': origin['postal_code'],
            'origin_country': origin['country'],
            'destination_facility': random.choice(FACILITIES),
            'destination_address_line1': destination['address_line1'],
            'destination_address_line2': destination['address_line2'],
            'destination_city': destination['city'],
            'destination_state': destination['state'],
            'destination_postal_code': destination['postal_code'],
            'destination_country': destination['country'],
            'destination_firstname': fake.first_name(),
            'planning_type': random.choice(PLANNING_TYPES),
            'pre_plan_transportation': random.choice([True, False]),
            'residential_destination': random.choice([True, False]),
            'post_office_box_destination': random.choice([True, False]),
            'pickup_start_datetime': pickup_start,
            'pickup_end_datetime': pickup_end,
            'delivery_start_datetime': delivery_start,
            'delivery_end_datetime': delivery_end,
            'order_placed_datetime': order_placed,
            'created_datetime': order_placed,
            'created_at': order_placed,
            'updated_at': order_placed
        })
    
    return orders

def generate_orderlines(orders: List[Dict], items: List[Dict]) -> List[Dict]:
    """Generate order lines data for the given orders."""
    orderlines = []
    order_id = 1  # Assuming order_id starts from 1

    for order in orders:
        # Generate between 1 and 5 order lines per order
        num_lines = random.randint(1, 5)
        
        for j in range(num_lines):
            item = random.choice(items)
            original_qty = random.randint(1, 100)
            allocated_qty = original_qty if random.random() < 0.8 else random.randint(0, original_qty)
            picked_qty = allocated_qty if random.random() < 0.9 else random.randint(0, allocated_qty)
            shipped_qty = picked_qty if random.random() < 0.95 else random.randint(0, picked_qty)

            orderlines.append({
                'order_id': order_id,
                'order_number': order['order_number'],
                'item_number': item['item_number'],
                'item_description': item['item_description'],
                'supplier_item_id': f"SUP{item['item_number'][4:]}",
                'shortage': allocated_qty < original_qty,
                'extension_run_number': f"RUN{random.randint(1000, 9999)}",
                'original_ordered_quantity': original_qty,
                'allocated_quantity': allocated_qty,
                'picked_quantity': picked_qty,
                'shipped_quantity': shipped_qty,
                'planning_mode': random.choice(PLANNING_MODES),
                'pipeline_status': random.choice(PIPELINE_STATUS),
                'order_sequence': j + 1,
                'assigned_shipment': f"SHIP{random.randint(10000, 99999)}",
                'assigned_stops': f"STOP{random.randint(1, 5)}",
                'assigned_ship_via': random.choice(SHIP_VIAS),
                'assigned_static_route': f"ROUTE{random.randint(100, 999)}",
                'created_datetime': order['created_datetime'],
                'created_at': order['created_datetime'],
                'updated_at': order['created_datetime']
            })
        
        order_id += 1
    
    return orderlines

def insert_data_into_db(conn, table_name: str, data: List[Dict]):
    """Insert data into the specified table."""
    if not data:
        return
    
    columns = ', '.join(data[0].keys())
    placeholders = ', '.join(['%s'] * len(data[0]))
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    
    cursor = conn.cursor()
    try:
        for row in data:
            values = list(row.values())
            cursor.execute(query, values)
        conn.commit()
    except Exception as e:
        print(f"Error inserting data into {table_name}: {e}")
        conn.rollback()
    finally:
        cursor.close()

def main():
    # Generate sample data
    items = [
        {
            'item_number': f"{ITEM_PREFIX}{str(i).zfill(6)}", 
            'item_description': f"Test Item {i}"
        } 
        for i in range(100)
    ]
    
    # Generate orders and order lines
    orders = generate_dc_orders(100)
    orderlines = generate_orderlines(orders, items)
    
    # Connect to TimescaleDB
    try:
        conn = psycopg2.connect(CONNECTION)
        
        # Insert data into tables
        insert_data_into_db(conn, 'dc_order', orders)
        insert_data_into_db(conn, 'orderlines', orderlines)
        
        print("Data inserted successfully!")
    except Exception as e:
        print(f"Error connecting to the database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()