import mysql.connector
import random
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import tempfile
import numpy as np

# MySQL Configuration
load_dotenv('config.env')
ssl_ca_content = os.environ.get('DB_SSL_CA_CONTENT')
if ssl_ca_content:
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
    temp_file.write(ssl_ca_content)
    temp_file.close()
DB_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'database': os.environ.get('DB_DATABASE'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'ssl_ca': temp_file.name,
    'ssl_verify_cert': bool(os.environ.get('DB_SSL_VERIFY_CERT', False))
}

random.seed(42)
np.random.seed(42)

# Product data with REALISTIC purchase patterns
PRODUCTS_DATA = {
    'Food & Beverage': [
        # (name, price, manufacturer, shelf_life, variants, avg_quantity_multiplier)
        ('Coca-Cola 330ml', 1.99, 'The Coca-Cola Company', 365, ['Pepsi 330ml'], 2.5),  # Cheap → buy more
        ('Dasani Water 500ml', 1.49, 'The Coca-Cola Company', 730, ['Aquafina'], 3.0),  # Very cheap → buy lots
        ('Oreo Original 303g', 4.99, 'Mondelez International', 270, ['Chips Ahoy'], 1.8),
        ('Maruchan Ramen Chicken', 0.99, 'Maruchan Inc', 180, ['Top Ramen'], 4.0),  # Very cheap → stock up
        ('Hershey Milk Chocolate', 1.49, 'The Hershey Company', 365, ['Cadbury'], 2.2),
    ],
    'Personal Care': [
        ('Colgate Toothpaste', 4.99, 'Colgate-Palmolive', 730, ['Crest'], 1.2),
        ('Head & Shoulders 400ml', 7.99, 'Procter & Gamble', 1095, ['Pantene'], 1.0),
        ('Dove Body Wash', 8.99, 'Unilever', 1095, ['Olay'], 1.0),
        ('Dove Beauty Bar 4pk', 5.49, 'Unilever', 1095, ['Irish Spring'], 1.3),
    ],
    'Home & Cleaning': [
        ('Lysol Cleaner 828ml', 4.99, 'Reckitt', 1095, ['Clorox'], 1.1),
        ('Tide Liquid 2.95L', 19.99, 'Procter & Gamble', 730, ['Persil'], 0.9),
        ('Dawn Dish Soap', 4.49, 'Procter & Gamble', 730, ['Palmolive'], 1.2),
    ],
    'Electronics': [
        ('Anker PowerBank 10000mAh', 24.99, 'Anker', 730, ['RAVPower'], 1.0),
        ('Logitech Mouse', 19.99, 'Logitech', 1095, ['Microsoft Mouse'], 1.0),
        ('USB-C Cable 6ft', 9.99, 'Anker', 730, ['Belkin'], 1.5),
    ],
    'Clothing': [
        ('Hanes T-Shirt', 12.99, 'Hanesbrands', 1825, ['Fruit of Loom'], 2.0),  # Basics → buy multiple
        ('Nike Shoes', 64.99, 'Nike Inc', 1825, ['Adidas'], 1.0),  # Expensive → buy one
        ('Cotton Socks 6pk', 9.99, 'Hanes', 1095, ['Gold Toe'], 1.8),
    ],
    'Baby Products': [
        ('Pampers Diapers 124ct', 38.99, 'Procter & Gamble', 1095, ['Huggies'], 2.5),  # Necessity → stock up
        ('Baby Wipes 560ct', 16.99, 'Kimberly-Clark', 1095, ['Pampers Wipes'], 2.0),
    ],
}

US_CITIES_STATES = [
    ('Seattle', 'WA'), ('Los Angeles', 'CA'), ('Chicago', 'IL'),
    ('Dallas', 'TX'), ('Atlanta', 'GA'), ('Phoenix', 'AZ'),
    ('New York', 'NY'), ('Miami', 'FL')
]

STREET_NAMES = ['Main St', 'Oak Ave', 'Maple Dr', 'Park Blvd', 'Washington St']


def generate_id(prefix, index):
    return f"{prefix}{str(index).zfill(8)}"


def random_date(start_date, end_date):
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)


def random_datetime_in_day(base_date):
    is_weekend = base_date.weekday() >= 5
    if is_weekend:
        hour = random.choices(range(9, 23), weights=[1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2, 1, 1], k=1)[0]
    else:
        hour = random.choices(range(8, 22), weights=[1, 1, 2, 3, 5, 4, 3, 2, 4, 6, 7, 5, 3, 2], k=1)[0]
    return base_date.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))


def calculate_realistic_quantity(product_price, product_multiplier, user_buying_power,
                                 is_weekend, is_promotion_month, hour):
    """
    Calculate realistic order quantity based on multiple factors
    """
    # Base quantity from product characteristics
    base_qty = product_multiplier

    # Price effect: cheaper items → buy more
    if product_price < 2:
        price_factor = 1.5
    elif product_price < 10:
        price_factor = 1.2
    elif product_price < 30:
        price_factor = 1.0
    else:
        price_factor = 0.8

    # User buying power (some users always buy more)
    user_factor = user_buying_power

    # Weekend effect (buy 20% more on weekends)
    weekend_factor = 1.2 if is_weekend else 1.0

    # Promotion month (Nov-Dec: holiday shopping, buy 30% more)
    promo_factor = 1.3 if is_promotion_month else 1.0

    # Peak hour effect (lunch and evening)
    if hour in [12, 13, 18, 19, 20]:
        time_factor = 1.15
    else:
        time_factor = 1.0

    # Calculate final quantity
    expected_qty = base_qty * price_factor * user_factor * weekend_factor * promo_factor * time_factor

    # Add some randomness but keep it realistic
    actual_qty = int(np.random.normal(expected_qty, expected_qty * 0.2))

    # Clamp to reasonable range
    return max(1, min(10, actual_qty))


def insert_users(cursor, conn, count=100):
    print(f"Inserting {count} users...")
    users = []

    first_names = ['James', 'John', 'Mary', 'Patricia', 'Michael', 'Jennifer', 'William', 'Linda']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis']

    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 11, 1)

    # Assign buying power to each user (some are big spenders)
    user_buying_powers = {}

    for i in range(count):
        user_id = generate_id('U', i + 1)
        nickname = f"{random.choice(first_names)}{random.choice(last_names)}{random.randint(100, 999)}"
        register_time = random_date(start_date, end_date)
        register_time = register_time.replace(hour=random.randint(8, 22), minute=random.randint(0, 59))

        # Assign buying power: 20% are "bulk buyers", 60% normal, 20% minimal
        buying_power = random.choices([0.7, 1.0, 1.5], weights=[0.2, 0.6, 0.2])[0]
        user_buying_powers[user_id] = buying_power

        users.append((user_id, nickname, register_time))

    cursor.executemany(
        "INSERT INTO users (user_id, nickname, register_time) VALUES (%s, %s, %s)",
        users
    )
    conn.commit()
    print(f"✓ Inserted {len(users)} users")
    return users, user_buying_powers


def insert_warehouses(cursor, conn):
    print("Inserting warehouses...")
    warehouse_locations = [
        ('1500 Logistics Pkwy', 'Seattle', 'WA', '98188'),
        ('2800 Distribution Dr', 'Los Angeles', 'CA', '90058'),
        ('4200 Warehouse Rd', 'Chicago', 'IL', '60638'),
        ('3600 Fulfillment Blvd', 'Dallas', 'TX', '75237'),
    ]

    warehouses = []
    for i, (street, city, state, zipcode) in enumerate(warehouse_locations):
        warehouse_id = generate_id('W', i + 1)
        location = f"{street}, {city}, {state} {zipcode}"
        warehouses.append((warehouse_id, location))

    cursor.executemany(
        "INSERT INTO warehouses (warehouse_id, location) VALUES (%s, %s)",
        warehouses
    )
    conn.commit()
    print(f"✓ Inserted {len(warehouses)} warehouses")
    return warehouses


def insert_products(cursor, conn, count=100):
    print(f"Inserting {count} products...")
    products = []
    product_details = {}  # Store product characteristics
    product_idx = 1

    total_base_products = sum(len(items) for items in PRODUCTS_DATA.values())

    for category, items in PRODUCTS_DATA.items():
        category_count = int(count * len(items) / total_base_products)
        products_per_item = max(1, category_count // len(items))

        for base_product, base_price, manufacturer, shelf_life, variants, qty_multiplier in items:
            for _ in range(products_per_item):
                if product_idx > count:
                    break

                product_id = generate_id('P', product_idx)

                if random.random() < 0.7 or not variants:
                    product_name = base_product
                    price = base_price * random.uniform(0.95, 1.05)
                else:
                    product_name = random.choice(variants)
                    price = base_price * random.uniform(0.90, 1.10)

                batch_date = datetime.now() - timedelta(days=random.randint(0, 365))
                batch_number = f"B{batch_date.year}{batch_date.month:02d}{batch_date.day:02d}{random.randint(1000, 9999)}"

                products.append(
                    (product_id, product_name, category, round(price, 2), manufacturer, shelf_life, batch_number))

                # Store product characteristics for later use
                product_details[product_id] = {
                    'price': round(price, 2),
                    'category': category,
                    'qty_multiplier': qty_multiplier
                }

                product_idx += 1
                if product_idx > count:
                    break
            if product_idx > count:
                break
        if product_idx > count:
            break

    cursor.executemany(
        "INSERT INTO products (product_id, product_name, type, price, manufacturer, shelf_life, batch_number) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        products
    )
    conn.commit()
    print(f"✓ Inserted {len(products)} products")
    return products, product_details


def insert_suppliers(cursor, conn, count=10):
    print(f"Inserting {count} suppliers...")
    suppliers = []

    prefixes = ['Global', 'Premier', 'United', 'Elite', 'Prime', 'Alpha', 'Metro', 'Pacific']
    suffixes = ['Supply Inc', 'Wholesale Corp', 'Distribution LLC', 'Trading Co', 'Logistics Group']

    for i in range(count):
        supplier_id = generate_id('S', i + 1)
        supplier_name = f"{random.choice(prefixes)} {random.choice(suffixes)} #{i + 1}"

        city, state = random.choice(US_CITIES_STATES)
        street = random.choice(STREET_NAMES)
        address = f"{random.randint(100, 9999)} {street}, {city}, {state} {random.randint(10000, 99999)}"

        star = random.choices([3, 4, 5], weights=[0.1, 0.4, 0.5])[0]
        duration = random.choices([random.randint(6, 24), random.randint(24, 60), random.randint(60, 120)],
                                  weights=[0.2, 0.5, 0.3])[0]
        status = random.choices(['active', 'inactive'], weights=[0.95, 0.05])[0]

        suppliers.append((supplier_id, supplier_name, address, star, duration, status))

    cursor.executemany(
        "INSERT INTO suppliers (supplier_id, supplier_name, address, star, duration, status) VALUES (%s, %s, %s, %s, %s, %s)",
        suppliers
    )
    conn.commit()
    print(f"✓ Inserted {len(suppliers)} suppliers")
    return suppliers


def insert_store_records(cursor, conn, products, warehouses):
    print("Inserting store records...")
    records = []

    for product in products:
        product_id = product[0]
        product_price = product[3]

        if product_price < 5:
            num_warehouses = random.randint(3, len(warehouses))
        elif product_price < 50:
            num_warehouses = random.randint(2, 3)
        else:
            num_warehouses = random.randint(1, 2)

        selected_warehouses = random.sample(warehouses, num_warehouses)

        for warehouse in selected_warehouses:
            if product_price < 5:
                quantity = random.randint(500, 2000)
            elif product_price < 20:
                quantity = random.randint(200, 800)
            else:
                quantity = random.randint(50, 300)

            records.append((warehouse[0], product_id, quantity))

    cursor.executemany(
        "INSERT INTO store_records (warehouse_id, product_id, storequantity) VALUES (%s, %s, %s)",
        records
    )
    conn.commit()
    print(f"✓ Inserted {len(records)} store records")
    return records


def insert_orders_realistic(cursor, conn, users, user_buying_powers, store_records,
                            product_details, order_count=2000):
    """
    Generate orders with REALISTIC patterns based on business logic
    """
    print(f"Inserting {order_count} orders with realistic patterns...")
    orders = []
    informs = []

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 11, 27)

    # Create product-warehouse mapping
    product_dict = {}
    for record in store_records:
        warehouse_id, product_id, store_qty = record
        if product_id not in product_dict:
            product_dict[product_id] = []
        product_dict[product_id].append((warehouse_id, store_qty))

    for i in range(order_count):
        order_id = f"ORD{datetime.now().year}{str(i + 1).zfill(10)}"
        user = random.choice(users)
        user_id = user[0]
        user_buying_power = user_buying_powers[user_id]

        order_date = random_date(start_date, end_date)
        order_time = random_datetime_in_day(order_date)

        is_weekend = order_date.weekday() >= 5
        is_promotion_month = order_date.month in [11, 12]  # Holiday season

        orders.append((order_id, user_id, order_time))

        # Number of items in order
        if user_buying_power > 1.2:  # Big buyers
            num_items = random.choices([1, 2, 3, 4], weights=[0.2, 0.3, 0.3, 0.2])[0]
        else:
            num_items = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]

        available_products = list(product_dict.keys())
        selected_products = random.sample(available_products, min(num_items, len(available_products)))

        for product_id in selected_products:
            warehouse_id, store_qty = random.choice(product_dict[product_id])

            # Get product characteristics
            product_info = product_details[product_id]
            product_price = product_info['price']
            qty_multiplier = product_info['qty_multiplier']

            # Calculate realistic quantity
            order_qty = calculate_realistic_quantity(
                product_price=product_price,
                product_multiplier=qty_multiplier,
                user_buying_power=user_buying_power,
                is_weekend=is_weekend,
                is_promotion_month=is_promotion_month,
                hour=order_time.hour
            )

            order_qty = min(order_qty, store_qty)

            status = random.choices(['pending', 'shipped', 'delivered'],
                                    weights=[0.05, 0.15, 0.80])[0]

            informs.append((order_id, product_id, warehouse_id, order_qty, status))

    cursor.executemany(
        "INSERT INTO orders (order_id, user_id, order_time) VALUES (%s, %s, %s)",
        orders
    )
    conn.commit()
    print(f"✓ Inserted {len(orders)} orders")

    cursor.executemany(
        "INSERT INTO inform (order_id, product_id, warehouse_id, orderquantity, status) VALUES (%s, %s, %s, %s, %s)",
        informs
    )
    conn.commit()
    print(f"✓ Inserted {len(informs)} order items")

    return orders, informs


def insert_good_supply(cursor, conn, suppliers, store_records):
    print("Inserting supply records...")
    supplies = []
    supply_keys = set()

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 11, 1)

    active_suppliers = [s for s in suppliers if s[5] == 'active']

    product_warehouse_map = {}
    for record in store_records:
        warehouse_id, product_id, _ = record
        if product_id not in product_warehouse_map:
            product_warehouse_map[product_id] = []
        product_warehouse_map[product_id].append(warehouse_id)

    for supplier in active_suppliers:
        num_products = random.randint(10, 20)
        available_products = list(product_warehouse_map.keys())
        selected_products = random.sample(available_products, min(num_products, len(available_products)))

        for product_id in selected_products:
            available_warehouses = product_warehouse_map[product_id]
            num_warehouses = min(random.randint(1, 2), len(available_warehouses))
            selected_warehouses = random.sample(available_warehouses, num_warehouses)

            for warehouse_id in selected_warehouses:
                supply_key = (supplier[0], product_id, warehouse_id)
                if supply_key in supply_keys:
                    continue
                supply_keys.add(supply_key)

                quantity = random.randint(200, 1000)
                supply_date = random_date(start_date, end_date)
                supply_time = supply_date.replace(hour=random.randint(8, 17),
                                                  minute=random.randint(0, 59))

                supplies.append((supplier[0], product_id, warehouse_id, quantity, supply_time))

    cursor.executemany(
        "INSERT INTO good_supply (supplier_id, product_id, warehouse_id, quantity, supply_time) VALUES (%s, %s, %s, %s, %s)",
        supplies
    )
    conn.commit()
    print(f"✓ Inserted {len(supplies)} supply records")


def insert_logistics(cursor, conn, orders):
    print("Inserting logistics data...")
    express_companies = [
        ('FedEx', (1, 3)), ('UPS', (1, 4)), ('USPS Priority', (2, 5)),
        ('Amazon Logistics', (1, 2)), ('DHL Express', (2, 4))
    ]

    logistics_records = []
    shipping_records = []
    delivery_records = []

    for i, order in enumerate(orders):
        logistics_id = generate_id('L', i + 1)
        order_id = order[0]
        order_time = order[2]

        express_company, (min_days, max_days) = random.choice(express_companies)
        logistics_status = random.choices(['in_transit', 'delivered'], weights=[0.10, 0.90])[0]

        logistics_records.append((logistics_id, order_id, express_company, logistics_status))

        shipping_delay = random.randint(2, 24) if order_time.hour < 18 else random.randint(12, 36)
        shipping_time = order_time + timedelta(hours=shipping_delay)

        city, state = random.choice(US_CITIES_STATES)
        street = random.choice(STREET_NAMES)
        apt = f" Apt {random.randint(1, 999)}" if random.random() < 0.4 else ""
        shipping_address = f"{random.randint(100, 9999)} {street}{apt}, {city}, {state} {random.randint(10000, 99999)}"

        shipping_records.append((logistics_id, shipping_time, shipping_address))

        if logistics_status == 'delivered':
            delivery_days = random.randint(min_days, max_days)
            temp_delivery = shipping_time + timedelta(days=delivery_days)
            if temp_delivery.weekday() == 6:
                delivery_days += 1
            delivery_time = shipping_time + timedelta(days=delivery_days, hours=random.randint(9, 20))
            delivery_records.append((logistics_id, delivery_time, shipping_address))

    cursor.executemany(
        "INSERT INTO logistics (logistics_id, order_id, express_company, logistics_status) VALUES (%s, %s, %s, %s)",
        logistics_records
    )
    conn.commit()
    print(f"✓ Inserted {len(logistics_records)} logistics records")

    cursor.executemany(
        "INSERT INTO shipping_product (logistics_id, shipping_time, shipping_address) VALUES (%s, %s, %s)",
        shipping_records
    )
    conn.commit()
    print(f"✓ Inserted {len(shipping_records)} shipping records")

    if delivery_records:
        cursor.executemany(
            "INSERT INTO delivery_product (logistics_id, delivery_time, delivery_address) VALUES (%s, %s, %s)",
            delivery_records
        )
        conn.commit()
        print(f"✓ Inserted {len(delivery_records)} delivery records")


def main():
    print("=" * 60)
    print("Generating REALISTIC data with ML patterns...")
    print("=" * 60)

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print(f"✓ Connected to database: {DB_CONFIG['database']}")

        cursor.execute("SET FOREIGN_KEY_CHECKS=0")

        # Insert data with business logic
        users, user_buying_powers = insert_users(cursor, conn, 100)
        warehouses = insert_warehouses(cursor, conn)
        products, product_details = insert_products(cursor, conn, 100)
        suppliers = insert_suppliers(cursor, conn, 10)
        store_records = insert_store_records(cursor, conn, products, warehouses)

        # Generate orders with realistic patterns
        orders, informs = insert_orders_realistic(
            cursor, conn, users, user_buying_powers,
            store_records, product_details, order_count=2000
        )

        insert_good_supply(cursor, conn, suppliers, store_records)
        insert_logistics(cursor, conn, orders)

        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()

        print("=" * 60)
        print("✓ Realistic data generated successfully!")
        print("=" * 60)
        print("\nKey improvements:")
        print("  ✅ Cheap products → higher quantities")
        print("  ✅ User buying habits (bulk buyers vs minimal)")
        print("  ✅ Weekend effect (20% more)")
        print("  ✅ Holiday season effect (30% more)")
        print("  ✅ Time-of-day effect")
        print("  ✅ Product-specific patterns")
        print("\nExpected ML performance: R² > 0.4")

    except Exception as err:
        print(f"✗ Error: {err}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("✓ Database connection closed")


if __name__ == "__main__":
    main()