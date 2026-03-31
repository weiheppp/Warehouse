import os
import tempfile
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
from PromotionAdvisor import PromotionAdvisor


class SalesAnalyzer:
    def __init__(self):
        # Load environment variables first
        load_dotenv('config.env')

        # Then get the constants
        self.ANALYSIS_DAYS = int(os.environ.get('ANALYSIS_DAYS', 30))
        self.LOW_SALES_THRESHOLD = int(os.environ.get('LOW_SALES_THRESHOLD', 10))

        # Database configuration
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
            'port': int(os.environ.get('DB_PORT', 5432)),
            'ssl_ca': temp_file.name,
            'ssl_verify_cert': bool(os.environ.get('DB_SSL_VERIFY_CERT')) == True
        }

        self.config = DB_CONFIG.copy()
        self.config['use_pure'] = True

    def _get_connection(self):
        """Connect to database"""
        try:
            return mysql.connector.connect(**self.config)
        except Error as e:
            print(f"Connection failed: {e}")
            return None

    def get_slow_moving_products(self, days=None):

        if days is None:
            days = self.ANALYSIS_DAYS

        conn = None
        cursor = None

        try:
            conn = self._get_connection()
            if not conn:
                return None

            cursor = conn.cursor(dictionary=True)

            # Fixed SQL query based on your actual table structure
            query = """
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
            LIMIT 50
            """

            cursor.execute(query)
            results = cursor.fetchall()

            # Convert datetime to string
            for row in results:
                if row.get('supply_time'):
                    row['supply_time'] = row['supply_time'].strftime('%Y-%m-%d %H:%M:%S')

            return results

        except Error as e:
            print(f"Query failed: {e}")
            print(f"Error details: {e}")
            return None

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_category_performance(self):

        conn = None
        cursor = None

        try:
            conn = self._get_connection()
            if not conn:
                return None

            cursor = conn.cursor(dictionary=True)

            query = """
            SELECT 
                p.type as category,
                COUNT(DISTINCT p.product_id) as total_products,
                AVG(sr.storequantity) as avg_stock,
                SUM(CASE 
                    WHEN sr.storequantity > 100 THEN 1 
                    ELSE 0 
                END) as high_stock_count
            FROM products p
            LEFT JOIN store_records sr ON p.product_id = sr.product_id
            GROUP BY p.type
            ORDER BY high_stock_count DESC
            """

            cursor.execute(query)
            results = cursor.fetchall()

            # Calculate percentages
            for row in results:
                if row['total_products'] > 0:
                    row['high_stock_percentage'] = round(
                        (row['high_stock_count'] / row['total_products']) * 100, 2
                    )
                else:
                    row['high_stock_percentage'] = 0.0

                # Round avg_stock
                if row['avg_stock']:
                    row['avg_stock'] = round(row['avg_stock'], 2)

            return results

        except Error as e:
            print(f"Query failed: {e}")
            return None

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def format_data_for_ai(self):
        """Format data for AI analysis"""
        slow_products = self.get_slow_moving_products()
        category_performance = self.get_category_performance()

        if not slow_products:
            return None

        # Build report for AI
        report = {
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'analysis_period': f'Products in stock for {self.ANALYSIS_DAYS}+ days',
            'low_sales_threshold': f'Less than {self.LOW_SALES_THRESHOLD}% sold',
            'slow_moving_products': slow_products,
            'category_performance': category_performance,
            'total_slow_products': len(slow_products)
        }

        return report

    def top5_slow_products(self):

        conn = None
        cursor = None

        try:
            conn = self._get_connection()
            if not conn:
                return None

            cursor = conn.cursor(dictionary=True)

            query = """
            SELECT 
                p.product_name,
                AVG(ROUND((gs.quantity - sr.storequantity) / gs.quantity, 2)) as sell_through_rate
            FROM good_supply gs
            LEFT JOIN store_records sr 
                ON gs.warehouse_id = sr.warehouse_id 
                AND gs.product_id = sr.product_id
            LEFT JOIN products p
                ON gs.product_id = p.product_id
            WHERE DATEDIFF(CURDATE(), DATE(gs.supply_time)) >= 10
                AND (gs.quantity - sr.storequantity) / gs.quantity < 0.3

            GROUP BY p.product_name

            ORDER BY sell_through_rate ASC
            LIMIT 5
            """

            cursor.execute(query)
            results = cursor.fetchall()

            return results

        except Error as e:
            print(f"Query failed: {e}")
            return None

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def price_vs_days(self):

        conn = None
        cursor = None

        try:
            conn = self._get_connection()
            if not conn:
                return None

            cursor = conn.cursor(dictionary=True)

            query = """
            SELECT 
                p.price,
                DATEDIFF(NOW(), gs.supply_time) as days_in_stock,
                p.product_name
            FROM products p
            JOIN good_supply gs ON p.product_id = gs.product_id
            WHERE gs.supply_time IS NOT NULL
                AND DATEDIFF(NOW(), gs.supply_time) > 0
            LIMIT 100
            """

            cursor.execute(query)
            results = cursor.fetchall()

            return results

        except Error as e:
            print(f"Query failed: {e}")
            return None

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def warehouse_distribution(self):

        conn = None
        cursor = None

        try:
            conn = self._get_connection()
            if not conn:
                return None

            cursor = conn.cursor(dictionary=True)

            query = """
            SELECT 
                w.location,
                w.warehouse_id,
                SUM(sr.storequantity) as total_stock
            FROM warehouses w
            JOIN store_records sr ON w.warehouse_id = sr.warehouse_id
            GROUP BY w.warehouse_id, w.location
            ORDER BY total_stock DESC
            """

            cursor.execute(query)
            results = cursor.fetchall()

            return results

        except Error as e:
            print(f"Query failed: {e}")
            return None

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_slow_moving_products_ML(self, days=30):
        """
        Get top 5 slowest-selling products with ML-required fields
        """
        conn = None
        cursor = None

        try:
            conn = self._get_connection()
            if not conn:
                return None

            query = """
            SELECT 
                MIN(p.product_id) as product_id,
                p.product_name,
                MIN(p.type) as category,
                AVG(p.price) as price,
                MIN(p.manufacturer) as manufacturer,
                MIN(gs.supplier_id) as supplier_id,
                MIN(sr.warehouse_id) as warehouse_id,
                SUM(sr.storequantity) AS stock_quantity,
                SUM(gs.quantity) AS supply_quantity,
                MAX(DATEDIFF(CURDATE(), DATE(gs.supply_time))) AS days_in_stock,

                SUM(COALESCE(
                    (SELECT SUM(i.orderquantity) 
                     FROM inform i 
                     JOIN orders o ON i.order_id = o.order_id
                     WHERE i.product_id = p.product_id 
                       AND o.order_time >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                    ), 0
                )) as monthly_sales,

                AVG(ROUND((gs.quantity - sr.storequantity) / gs.quantity, 2)) as sell_through_rate

            FROM good_supply gs
            LEFT JOIN store_records sr 
                ON gs.warehouse_id = sr.warehouse_id 
                AND gs.product_id = sr.product_id
            LEFT JOIN products p
                ON gs.product_id = p.product_id

            WHERE DATEDIFF(CURDATE(), DATE(gs.supply_time)) >= 10
                AND (gs.quantity - sr.storequantity) / gs.quantity < 0.4
                AND sr.storequantity > 30

            GROUP BY p.product_name

            HAVING monthly_sales < 20

            ORDER BY sell_through_rate ASC
            LIMIT 5;
            """

            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            products = cursor.fetchall()

            return products

        except Exception as e:
            print(f"Error: {e}")
            return []

        finally:
            if conn:
                conn.close()