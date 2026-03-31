from database import DatabaseManager
from db_config import create_user, create_store, create_orders,create_product,create_information
from db_config import create_delivery, create_logistic, create_warehouses, create_shipping
from db_config import create_supplier, create_good_supply
import time

if __name__ == "__main__":
    db = DatabaseManager()
    sql_statements = [
        create_user, create_store, create_orders, create_product, create_information,
        create_delivery, create_logistic, create_warehouses, create_shipping,
        create_supplier, create_good_supply
    ]


    if not db.connect():
        print("connect database fail")
        exit(1)

    # start create
    print("\nstart create table...")
    success_count = 0

    for i, sql in enumerate(sql_statements, 1):
        print(f"\n[{i}/{len(sql_statements)}] creating...")

        if db.execute_sql(sql):
            success_count += 1
            print(f"successful")
        else:
            print(f"fail")

        time.sleep(0.3)  # insert sleep avoid sync up error

    print(f"\n{'=' * 60}")
    print(f"Successful table information: {success_count}/{len(sql_statements)} ")
    print(f"{'=' * 60}")

    db.close()