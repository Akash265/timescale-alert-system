import psycopg2
import pandas as pd
CONNECTION = "postgres://tsdbadmin:m362xngx89whn28r@rmjil6bz1d.hlsqzxo5q3.tsdb.cloud.timescale.com:39236/tsdb?sslmode=require"
conn = psycopg2.connect(CONNECTION)
cursor = conn.cursor()
# use the cursor to interact with your database
query = """SELECT enumlabel FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'status_enum');
"""
cursor.execute(query)
# Query the information_schema.columns to check for 'status' in 'alert_config'
cursor.execute("""
            UPDATE alert_config
            SET query = %s
            WHERE name = %s
        """, (
            "SELECT * FROM dc_order WHERE created_at > NOW() - INTERVAL '5 minutes'",
            "Test Alert"
        ))
cursor.execute("""
                INSERT INTO dc_order (
    business_unit, order_number, priority, maximum_status, order_type, pipeline,
    origin_facility, origin_address_line1, origin_city, origin_state, origin_postal_code, origin_country,
    destination_facility, destination_address_line1, destination_city, destination_state, destination_postal_code, destination_country,
    destination_firstname, planning_type, pre_plan_transportation, residential_destination, post_office_box_destination,
    pickup_start_datetime, pickup_end_datetime, delivery_start_datetime, delivery_end_datetime,
    order_placed_datetime, created_datetime, created_at, updated_at
) VALUES (
    'SEP01', 'ORD000000120', 'MEDIUM', 'CREATED', 'SO', 'ECOMM',
    'DC1', '123 Main St', 'Springfield', 'IL', '62701', 'USA',
    'DC2', '456 Oak Ave', 'Shelbyville', 'IL', '62565', 'USA',
    'John', 'WAVE', TRUE, FALSE, FALSE,
    '2025-03-04 10:00:00+00', '2025-03-04 14:00:00+00',
    '2025-03-05 09:00:00+00', '2025-03-05 17:00:00+00',
    NOW(), NOW(),
    NOW(), NOW()
);
            """)
conn.commit()
cursor.execute("""
                SELECT * FROM dc_order WHERE created_at > NOW() - INTERVAL '5 minutes'
            """)
result = cursor.fetchone()
print(cursor.fetchall())

conn.rollback()
# Define the query to select all data from the 'asn' table
query = "SELECT * FROM dc_order;"

# Execute the query
cursor.execute(query)

# Fetch all the results
data = cursor.fetchall()

# Fetch column names from the cursor
columns = [desc[0] for desc in cursor.description]

# Create a pandas DataFrame
df = pd.DataFrame(data, columns=columns)

# Close the cursor and connection
cursor.close()
connection.close()

# Print the DataFrame to see the data
print(df)