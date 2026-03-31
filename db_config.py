create_user = '''
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;
CREATE TABLE users (
user_id VARCHAR(32) PRIMARY KEY,
nickname VARCHAR(64),
register_time DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''
create_orders = '''
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS orders;
SET FOREIGN_KEY_CHECKS = 1;
CREATE TABLE orders (
order_id VARCHAR(64) PRIMARY KEY,
user_id VARCHAR(32),
order_time DATETIME,
FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

create_warehouses = '''
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS warehouses;
SET FOREIGN_KEY_CHECKS = 1;
CREATE TABLE warehouses (
warehouse_id VARCHAR(32) PRIMARY KEY,
location VARCHAR(128)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

create_product = '''
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS products;
SET FOREIGN_KEY_CHECKS = 1;
CREATE TABLE products (
product_id VARCHAR(32) PRIMARY KEY,
product_name VARCHAR(128),
type VARCHAR(64),
price DECIMAL(10,2),
manufacturer VARCHAR(128),
shelf_life INT,
batch_number VARCHAR(64)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
'''

create_store = '''
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS store_records;
SET FOREIGN_KEY_CHECKS = 1;
CREATE TABLE store_records (
warehouse_id VARCHAR(32) NOT NULL,
product_id VARCHAR(32) NOT NULL,
storequantity INT,
PRIMARY KEY (product_id, warehouse_id),
FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

create_information = '''
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS inform;
SET FOREIGN_KEY_CHECKS = 1;
CREATE TABLE inform (
order_id VARCHAR(64) NOT NULL,
product_id VARCHAR(32) NOT NULL,
warehouse_id VARCHAR(32) NOT NULL,
orderquantity INT,
status VARCHAR(32),
PRIMARY KEY (order_id, product_id, warehouse_id),
FOREIGN KEY (order_id) REFERENCES orders(order_id),
FOREIGN KEY (product_id, warehouse_id) REFERENCES store_records(product_id,
warehouse_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

create_supplier = '''
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS suppliers;
SET FOREIGN_KEY_CHECKS = 1;
CREATE TABLE suppliers (
supplier_id VARCHAR(32) PRIMARY KEY,
supplier_name VARCHAR(128),
address VARCHAR(256),
star INT,
duration INT,
status VARCHAR(32)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

create_good_supply = '''
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS good_supply;
SET FOREIGN_KEY_CHECKS = 1;
CREATE TABLE good_supply (
supplier_id VARCHAR(32) NOT NULL,
product_id VARCHAR(32) NOT NULL,
warehouse_id VARCHAR(32) NOT NULL,
quantity INT,
supply_time DATETIME,
PRIMARY KEY (supplier_id, product_id, warehouse_id),
FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
FOREIGN KEY (product_id, warehouse_id) REFERENCES store_records(product_id,
warehouse_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

create_logistic = '''
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS logistics;
SET FOREIGN_KEY_CHECKS = 1;
CREATE TABLE logistics (
logistics_id VARCHAR(32) PRIMARY KEY,
order_id VARCHAR(64) NOT NULL,
express_company VARCHAR(64),
logistics_status VARCHAR(32),
FOREIGN KEY (order_id) REFERENCES orders(order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

create_shipping = '''
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS shipping_product;
SET FOREIGN_KEY_CHECKS = 1;
CREATE TABLE shipping_product (
logistics_id VARCHAR(32) PRIMARY KEY,
shipping_time DATETIME,
shipping_address VARCHAR(256),
FOREIGN KEY (logistics_id) REFERENCES logistics(logistics_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

create_delivery = '''
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS delivery_product;
SET FOREIGN_KEY_CHECKS = 1;
CREATE TABLE delivery_product (
logistics_id VARCHAR(32) PRIMARY KEY,
delivery_time DATETIME,
delivery_address VARCHAR(256),
FOREIGN KEY (logistics_id) REFERENCES logistics(logistics_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''

