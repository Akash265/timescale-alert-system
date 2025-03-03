-- Inventory Alerts
--Stock Level Alerts

SELECT i.item_number, i.total_on_hand, i.safety_stock_quantity
FROM item_inventory i
WHERE i.total_on_hand <= i.safety_stock_quantity

--Inventory Accuracy
SELECT li.location_number, li.item_number,
       li.current_quantity, SUM(l.quantity) as lpn_quantity
FROM location_inventory li
LEFT JOIN lpn_details l ON li.location_number = l.location_number 
   AND li.item_number = l.item_number
GROUP BY li.location_number, li.item_number, li.current_quantity
HAVING li.current_quantity != SUM(l.quantity)

-- Order Fulfillment Alerts
-- Late Order Alerts
SELECT order_number, delivery_end_datetime
FROM dc_order
WHERE delivery_end_datetime < CURRENT_TIMESTAMP
  AND maximum_status != 'DELIVERED'

--Order Line Shortages

SELECT ol.order_number, ol.item_number
FROM orderlines ol
WHERE ol.shortage = true  

--ASN/Receipt Alerts
--Overdue ASNs
SELECT asn_number, estimated_delivery_date
FROM asn
WHERE estimated_delivery_date < CURRENT_TIMESTAMP
  AND received_qty IS NULL

--Receipt Discrepancies  
SELECT asn_number, shipped_qty, received_qty
FROM asn
WHERE received_qty < shipped_qty
  AND process_status = 'RECEIVED'

--Location Management  
--Location Utilization

SELECT l.zone, 
       COUNT(*) as total_locations,
       SUM(CASE WHEN li.current_quantity > 0 THEN 1 ELSE 0 END) as used_locations
FROM storage_location l
LEFT JOIN location_inventory li ON l.location_number = li.location_number
GROUP BY l.zone
HAVING (SUM(CASE WHEN li.current_quantity > 0 THEN 1 ELSE 0 END)::float / COUNT(*)) > 0.9

--Trend-based Alerts
--Unusual Pick Patterns]
SELECT i.item_number, i.picks_last_30_days
FROM item_inventory i
WHERE i.picks_last_30_days > 
      (SELECT AVG(picks_last_30_days) + 2 * STDDEV(picks_last_30_days)
       FROM item_inventory)

--Quality Alerts       
SELECT l.lpn_number, l.item_number, l.expiration_date
FROM lpn_details l
WHERE l.expiration_date < CURRENT_DATE + INTERVAL '30 days'
  AND l.quantity > 0

--Alert Implementation  

    -- Create a scheduled job that runs these queries periodically
    -- Store alert configurations in a separate table:

CREATE TABLE alert_configurations (
    id serial PRIMARY KEY,
    alert_type VARCHAR(50),
    alert_query TEXT,
    frequency INTERVAL,
    severity VARCHAR(20),
    threshold NUMERIC,
    enabled BOOLEAN,
    notification_channels JSON,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

--Alert History
CREATE TABLE alert_history (
    id serial PRIMARY KEY,
    alert_configuration_id INTEGER,
    alert_data JSONB,
    status VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ,
    FOREIGN KEY (alert_configuration_id) REFERENCES alert_configurations(id)
);