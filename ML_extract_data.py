import pandas as pd
from database import DatabaseManager


class ml_data():
    def __init__(self):
        self.mysql = DatabaseManager()
        self.mysql.connect()  # test connect

    def extract(self):
        query = """
        SELECT 
            o.order_id,
            o.order_time,
            p.product_id,
            p.product_name,
            p.type as product_category,
            p.price,
            p.manufacturer,
            i.orderquantity,
            i.status as order_status,
            w.warehouse_id,
            w.location as warehouse_location,
            u.user_id,
            HOUR(o.order_time) as order_hour,
            DAYOFWEEK(o.order_time) as order_day,
            MONTH(o.order_time) as order_month
        FROM orders o
        JOIN inform i ON o.order_id = i.order_id
        JOIN products p ON i.product_id = p.product_id
        JOIN warehouses w ON i.warehouse_id = w.warehouse_id
        JOIN users u ON o.user_id = u.user_id
        WHERE o.order_time >= '2024-01-01'
        """

        # conncect to database
        conn = self.mysql.get_connection()

        try:
            # read data from database
            df = pd.read_sql(query, conn)
            return df
        finally:
            if conn:
                conn.close()


test = ml_data()
df = test.extract()

# Save to CSV for future use
save_csv = True
if save_csv:
   df.to_csv('warehouse_data.csv', index=False)
   print("\n✓ Data saved to 'warehouse_data.csv'")
