import os
import sys
import json
from datetime import datetime
import time
from threading import Thread
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import traceback
from bson.objectid import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv


load_dotenv('config.env')
# MongoDB Configuration
# Connection URI (adjust as needed for remote/Atlas connections)
MONGO_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("MONGODB_NAME")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME")


class HistoryDB:
    """
    Handles asynchronous saving of AI-generated reports to MongoDB.
    """

    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self.is_connected = False
        try:
            # Set serverSelectionTimeoutMS to prevent blocking indefinitely if MongoDB is down
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')

            self.db = self.client[DB_NAME]
            self.collection = self.db[COLLECTION_NAME]
            self.is_connected = True
            print(f"✓ HistoryDB Handler initialized and connected to {DB_NAME}.{COLLECTION_NAME}")

        except Exception as e:
            print(f"✗ MongoDB connection failed. Please ensure MongoDB is running locally at {MONGO_URI}.",
                  file=sys.stderr)
            print(f"Error details: {e}", file=sys.stderr)
            self.is_connected = False

        print("✓ HistoryDB Handler initialization finished.")
        print("✓ HistoryDB Handler initialized.")

    def save_report_to_mongodb_async(self, report_document):
        """
        Connects to MongoDB and asynchronously inserts the structured report document.
        Note: The heavy database connection and insertion is run in a separate thread
        by the caller (`app.py:run_ai_analysis`).
        """
        # Note: The database connection and insertion logic is kept here.
        try:
            # 1. Connect to MongoDB
            # Set serverSelectionTimeoutMS to prevent blocking indefinitely if MongoDB is down
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # Attempt a command to confirm connection
            client.admin.command('ping')
            db = client[DB_NAME]
            collection = db[COLLECTION_NAME]

            # 2. Insert the document
            # MongoDB native support handles datetime objects automatically
            result = collection.insert_one(report_document)

            print(
                f"\n[MongoDB SAVE SUCCESS] Report saved as document ID: {result.inserted_id} into {DB_NAME}.{COLLECTION_NAME}")

        except ServerSelectionTimeoutError as e:
            print(f"\n[MongoDB SAVE FAILED] Connection Error. Make sure MongoDB service is running at {MONGO_URI}.")
            print(f"Error Details: {e}")
        except Exception as e:
            print(f"\n[MongoDB SAVE FAILED] An unexpected error occurred during insertion: {e}")
            traceback.print_exc()
        finally:
            # Ensure the client connection is closed
            if 'client' in locals() and client:
                client.close()

    def get_all_reports(self) -> list:

        if not self.is_connected:
            print(f"✗ Cannot retrieve reports. MongoDB connection failed during initialization.", file=sys.stderr)
            return []

        reports_list = []

        try:
            pipeline = [

                {'$unwind': {'path': '$recommendations', 'includeArrayIndex': 'index'}},


                {'$project': {
                    '_id': {'$toString': '$_id'},
                    'timestamp': '$creation_timestamp',
                    'index': 1,
                    'product_name': '$recommendations.Product Name',
                    'supply_name': '$recommendations.Supply Name',
                    'analysis': '$recommendations.Analysis',
                    'promotional_strategy': '$recommendations.Promotional Strategy'
                }},

                {'$sort': {'timestamp': -1, 'index': 1}},

                {'$limit': 100}
            ]

            results = self.collection.aggregate(pipeline)

            for doc in results:

                if 'timestamp' in doc and isinstance(doc['timestamp'], datetime):
                    doc['timestamp'] = doc['timestamp'].isoformat()

                reports_list.append(doc)

            print(f"✓ Retrieved {len(reports_list)} recommendations from MongoDB")
            return reports_list

        except Exception as e:
            print(f"✗ Error retrieving reports from MongoDB: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return []

    def delete_report_by_id(self, report_id: str) -> bool:

        try:
            object_id = ObjectId(report_id)

            result = self.collection.delete_one({'_id': object_id})

            if result.deleted_count == 1:
                print(f"✓ Report {report_id} deleted successfully.")
                return True
            else:
                print(f"✗ Report {report_id} not found for deletion.")
                return False

        except InvalidId:
            print(f"✗ Invalid report ID format: {report_id}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"✗ Error deleting report {report_id} from MongoDB: {e}", file=sys.stderr)
            return False

    def close(self):

        if self.client:
            self.client.close()
            print("MongoDB connection closed.")