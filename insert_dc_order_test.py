# insert_dc_order_test.py
import psycopg2

CONNECTION = "postgres://tsdbadmin:m362xngx89whn28r@rmjil6bz1d.hlsqzxo5q3.tsdb.cloud.timescale.com:39236/tsdb?sslmode=require"
conn = psycopg2.connect(CONNECTION)
cursor = conn.cursor()

try:
    cursor.execute("""
        INSERT INTO dc_order (
            business_unit, order_number, priority, pipeline, created_at
        ) VALUES (
            'SEP01', 'ORD00000000001', 'HIGH', 'ECOMM', NOW()
        );
    """)
    conn.commit()
    print("Inserted 1 row into dc_order successfully!")
except psycopg2.Error as e:
    print(f"Error inserting row: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()