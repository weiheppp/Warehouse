-- 1  This query checks which products in the warehouse have a low stock level.
-- We join the warehouse, product, and inventory tables, then filter items with quantity below 100.
-- The goal is to help the system send early alerts so managers can restock in time.
SELECT
  sr.warehouse_id,
  w.location AS warehouse_location,
  sr.product_id,
  p.product_name,
  p.type,
  p.manufacturer,
  sr.storequantity
FROM store_records sr
JOIN products p ON sr.product_id = p.product_id
JOIN warehouses w ON sr.warehouse_id = w.warehouse_id
WHERE sr.storequantity < 100
ORDER BY sr.storequantity ASC;

-- 2. Here we find slow-moving products.
-- We look for items that have been in stock for more than 10 days and have a sell-through rate below 40%.
-- We combine supply and store records to calculate stock, supply amount, and sell-through.
-- These results are later used to feed our AI to generate promotional strategies.
SELECT
MIN(gs.supplier_id) as supplier_id,
MIN(p.product_id) as product_id,
p.product_name,
MIN(p.type) as type,
AVG(p.price) as price,
MIN(p.manufacturer) as manufacturer,
SUM(sr.storequantity) as stock_quantity,
SUM(gs.quantity) as supply_quantity,
MIN(sr.warehouse_id) as warehouse_id,
MIN(gs.supply_time) as supply_time,
MAX(DATEDIFF(CURDATE(), DATE(gs.supply_time))) as days_in_stock,
AVG(ROUND((gs.quantity - sr.storequantity) / gs.quantity, 2)) as sell_through_rate
FROM good_supply gs
LEFT JOIN store_records sr
ON gs.warehouse_id = sr.warehouse_id
AND gs.product_id = sr.product_id
LEFT JOIN products p
ON gs.product_id = p.product_id
WHERE DATEDIFF(CURDATE(), DATE(gs.supply_time)) >= 10
AND (gs.quantity - sr.storequantity) / gs.quantity < 0.4
GROUP BY p.product_name
ORDER BY sell_through_rate ASC
LIMIT 50;

-- 3 This query finds products with more than 1,000 units in stock.
-- We join products, warehouses, suppliers, and supply records 
-- to show where the product is stored and who supplied it.
-- The purpose is to help inventory managers plan redistribution 
-- or decide how to use extra stock.
SELECT
p.product_name,
p.manufacturer,
p.price,
w.location AS warehouse_location,
sr.storequantity,
s.supplier_name,
gs.supply_time
FROM products p
INNER JOIN store_records sr ON p.product_id = sr.product_id
INNER JOIN warehouses w ON sr.warehouse_id = w.warehouse_id
INNER JOIN good_supply gs ON p.product_id = gs.product_id AND sr.warehouse_id = gs.warehouse_id
INNER JOIN suppliers s ON gs.supplier_id = s.supplier_id
WHERE sr.storequantity > 1000
ORDER BY sr.storequantity DESC
LIMIT 20;

-- 4 Here we check each user's activity.
-- We count how many orders they made and calculate their total spending.
-- Users who never placed an order show up with zero orders and zero spending.
-- This helps the marketing team identify dormant users for re-activation campaigns.
SELECT
u.user_id,
u.nickname,
u.register_time,
COUNT(o.order_id) AS order_count,
COALESCE(SUM(i.orderquantity * p.price), 0) AS total_spent
FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id
LEFT JOIN inform i ON o.order_id = i.order_id
LEFT JOIN products p ON i.product_id = p.product_id
GROUP BY u.user_id, u.nickname, u.register_time
ORDER BY total_spent DESC;

-- 5 This query finds “premium products” within each brand.
-- We compare a product’s price with the average price of the same manufacturer.
-- If a product is priced above its brand’s average, we treat it as a premium item.
-- This supports pricing and promotional strategies.
SELECT
p1.product_id,
p1.product_name,
p1.manufacturer,
p1.price,
(SELECT AVG(p2.price)
FROM products p2
WHERE p2.manufacturer = p1.manufacturer) AS avg_manufacturer_price
FROM products p1
WHERE p1.price > (
SELECT AVG(p2.price)
FROM products p2
WHERE p2.manufacturer = p1.manufacturer
)
ORDER BY p1.manufacturer, p1.price DESC;

-- 6 Here we identify warehouses with unusually high total inventory.
-- We calculate the total stock for each warehouse and compare it 
-- with the average stock across all warehouses.
-- Warehouses above the average are marked as “excess inventory,” 
-- which helps decide redistribution or clearance.
SELECT
w.warehouse_id,
w.location,
(SELECT COUNT(*)
FROM store_records sr1
WHERE sr1.warehouse_id = w.warehouse_id) AS product_count,
(SELECT SUM(sr2.storequantity)
FROM store_records sr2
WHERE sr2.warehouse_id = w.warehouse_id) AS total_inventory
FROM warehouses w
WHERE (
SELECT SUM(sr3.storequantity)
FROM store_records sr3
WHERE sr3.warehouse_id = w.warehouse_id
) > (
SELECT AVG(warehouse_total)
FROM (
SELECT SUM(sr4.storequantity) AS warehouse_total
FROM store_records sr4
GROUP BY sr4.warehouse_id
) AS avg_calc
)
ORDER BY total_inventory DESC;

--  7 This query finds products that have never been ordered.
-- If a product does not appear in the order details table, 
-- it's considered “never purchased.”
-- This helps managers decide whether to remove these items or create special promotions.
SELECT
p.product_id,
p.product_name,
p.manufacturer,
p.price
FROM products p
WHERE NOT EXISTS (
SELECT 1
FROM inform i
WHERE i.product_id = p.product_id
)
ORDER BY p.product_name;

-- 8 This query collects all types of addresses in the system—delivery, shipping, warehouses, and suppliers.
-- We combine them using UNION to create one list.
-- The logistics team uses this to build a nationwide service map.
SELECT 'Delivery' AS address_type, delivery_address AS address, COUNT(*) AS usage_count
FROM delivery_product
GROUP BY delivery_address
UNION
SELECT 'Shipping' AS address_type, shipping_address AS address, COUNT(*) AS usage_count
FROM shipping_product
GROUP BY shipping_address
UNION
SELECT 'Warehouse' AS address_type, location AS address, 1 AS usage_count
FROM warehouses
UNION
SELECT 'Supplier' AS address_type, address AS address, 1 AS usage_count
FROM suppliers
ORDER BY address_type, usage_count DESC;

-- 9 Here we evaluate logistics company performance.
-- We calculate their delivery success rate and average delivery days.
-- This helps directors choose which courier to cooperate with 
-- and how to allocate next-quarter shipping volume.
SELECT
express_company,
total_orders,
delivered_orders,
ROUND(delivered_orders * 100.0 / total_orders, 2) AS delivery_rate,
avg_delivery_days
FROM (
SELECT
l.express_company,
COUNT(*) AS total_orders,
SUM(CASE WHEN l.logistics_status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders,
AVG(
CASE
WHEN l.logistics_status = 'delivered'
THEN DATEDIFF(dp.delivery_time, sp.shipping_time)
ELSE NULL
END
) AS avg_delivery_days
FROM logistics l
LEFT JOIN shipping_product sp ON l.logistics_id = sp.logistics_id
LEFT JOIN delivery_product dp ON l.logistics_id = dp.logistics_id
GROUP BY l.express_company
) AS logistics_stats
ORDER BY delivery_rate DESC, avg_delivery_days ASC;

-- 10 This query finds suppliers who only provide products priced above $1.
-- We exclude any supplier who has even one low-priced product.
-- The result helps procurement select high-end suppliers for premium partnerships.
SELECT DISTINCT
s.supplier_id,
s.supplier_name,
s.star,
COUNT(DISTINCT gs.product_id) AS products_supplied,
MIN(p.price) AS min_product_price,
MAX(p.price) AS max_product_price
FROM suppliers s
JOIN good_supply gs ON s.supplier_id = gs.supplier_id
JOIN products p ON gs.product_id = p.product_id
WHERE s.supplier_id NOT IN (
-- Exclude suppliers who have ANY product below $1
SELECT DISTINCT gs2.supplier_id
FROM good_supply gs2
JOIN products p2 ON gs2.product_id = p2.product_id
WHERE p2.price < 1
)
GROUP BY s.supplier_id, s.supplier_name, s.star
HAVING COUNT(DISTINCT gs.product_id) > 0
ORDER BY min_product_price DESC;