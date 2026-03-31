import warnings
warnings.filterwarnings('ignore', message='.*urllib3 v2.*')

from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import sys
from threading import Thread
from datetime import datetime
from decimal import Decimal
import traceback
import joblib
import numpy as np

from SalesAnalyzer import SalesAnalyzer
from PromotionAdvisor import PromotionAdvisor
from Scheduler import PromotionScheduler
from mongoDB import HistoryDB
from ChartDesign import ChartDesign

# --- Flask  init ---
app = Flask(__name__)
# start CORS
CORS(app, origins=[
    "https://wan519.github.io",  # GitHub Pages
    "http://127.0.0.1:5000",     # 本地测试
    "http://localhost:5000"
])

# global
latest_report = None
last_analysis_time = None
is_analyzing = False


# Load model
try:
    model = joblib.load('models/demand_forecast_model.pkl')
    le_category = joblib.load('models/category_encoder.pkl')
    le_warehouse = joblib.load('models/warehouse_encoder.pkl')
    print("✓ ML models loaded successfully")
except Exception as e:
    print(f"Warning: ML models not loaded - {e}")
    model = None

try:
    # init AI
    advisor = PromotionAdvisor()
    # Init database
    Analyzer = SalesAnalyzer()
    # init mongodb
    db_handler = HistoryDB()

except EnvironmentError as e:
    # Failure to initialize due to missing API Key or other environment issues
    print(f"Flask Server failed to initialize PromotionAdvisor: {e}", file=sys.stderr)
    advisor = None
    Analyzer = None
    db_handler = None
except Exception as e:
    print(f"Flask Server failed to initialize PromotionAdvisor: {e}", file=sys.stderr)
    advisor = None
    Analyzer = None
    db_handler = None


def convert_decimals(obj):
    """Recursively converts all Decimal types in an object to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    else:
        return obj

def extract_table_data(markdown_text):
    """
    Extracts data from a Markdown table (skipping header and separator)
    and converts it into a structured list of dictionaries [{}, {}].
    This version uses a robust search to find the Header and Separator lines anywhere in the input.
    """
    if not markdown_text:
        return []

    # 1. Clean up input: remove empty lines and strip whitespace
    lines = markdown_text.strip().split('\n')
    processed_lines = [line.strip() for line in lines if line.strip()]

    if len(processed_lines) < 2:
        # Not enough lines for a header and separator
        print("✗ Markdown table structure not found (input has less than 2 meaningful lines).")
        return []

    header_index = -1
    separator_index = -1

    # 2. Iterate to find the first valid Header-Separator pair
    # We start checking from the second line (index 1) because the separator must follow a header.
    for i in range(1, len(processed_lines)):
        current_line = processed_lines[i]
        previous_line = processed_lines[i - 1]

        # Check if the current line is a valid separator (starts with '|' and contains '---')
        is_separator = current_line.startswith('|') and '---' in current_line

        # Check if the previous line is a valid header (starts with '|' and is NOT a separator)
        is_header = previous_line.startswith('|') and '---' not in previous_line

        if is_header and is_separator:
            header_index = i - 1
            separator_index = i
            break

    if header_index == -1:
        # If the search failed to find the pair
        print("✗ Markdown table structure not found (could not find a valid Header-Separator pair starting with '|').")
        return []

    # 3. Extract Header and Data lines
    header_line = processed_lines[header_index]
    # separator_line is processed_lines[separator_index] (not explicitly needed)
    data_lines = processed_lines[separator_index + 1:]

    # 4. Extract Headers
    # Filter out empty | cells, and remove Markdown bold markers (if any were missed by the Advisor)
    headers = [h.strip().replace('**', '') for h in header_line.split('|') if h.strip()]

    data_rows = []
    # Parse data rows
    for line in data_lines:
        if not line.startswith('|'):
            # Stop if we hit a non-table line after the separator
            break

        # Split cells, filter out empty strings, and clean content
        cells = [c.strip().replace('**', '')
                 for c in line.split('|') if c.strip()]

        if len(cells) == len(headers):
            # Map cells to headers
            row_data = {headers[i]: cells[i] for i in range(len(headers))}
            data_rows.append(row_data)

    if not data_rows:
        print("✗ Extracted table has zero data rows.")

    return data_rows


def run_ai_analysis():
    """
    Executes the full AI analysis workflow: Fetch data -> Call AI -> Cache result -> Asynchronously save structured data.
    """
    global latest_report, last_analysis_time, is_analyzing

    if is_analyzing:
        print("Analysis already in progress, skipping...")
        return

    is_analyzing = True

    try:
        # Get data from the analyzer (mock or DB query)
        data_from_db = Analyzer.format_data_for_ai()
        if data_from_db is None:
            print("✗ Database retrieval failed or returned no data.")
            is_analyzing = False
            return
        print("✓ Data retrieved from database")

        # Call AI module to get the raw Markdown string
        suggestions_markdown = advisor.get_suggestions(data_from_db)
        print("✓ AI suggestions generated")


        # Prepare the frontend response (contains original data and raw Markdown)
        response_data = {
            "products": data_from_db,  # Original data (for charts and KPIs)
            "suggestions": suggestions_markdown  # Raw AI report (Markdown format)
        }

        # Extract structured data (for database saving/JSON file)
        table_data_list = extract_table_data(suggestions_markdown)
        print(f"✓ Extracted {len(table_data_list)} suggestion rows for saving")

        # Asynchronously save the cleaned structured data
        report_document = {
            "creation_timestamp": datetime.now(),
            "recommendations": convert_decimals(table_data_list),
            "raw_source_data_snapshot": convert_decimals(data_from_db)
        }

        # Asynchronously save the structured data to MongoDB
        Thread(target=db_handler.save_report_to_mongodb_async, args=(report_document,), daemon=True).start()

        # Cache the result
        latest_report = response_data
        last_analysis_time = datetime.now()

        print("Analysis completed successfully!")

    except Exception as e:
        print(f"✗ Error during analysis: {e}")
        traceback.print_exc()
    finally:
        is_analyzing = False


def predict_quantity(category, price, warehouse_id):
    """
    Use ML model to predict order quantity at given price
    """
    if model is None:
        return 1.0
    try:
        # Encode categorical features
        try:
            category_encoded = le_category.transform([category])[0]
        except Exception as e:
            print(f"Category encoding error: {e}")
            return 1.0

        try:
            warehouse_encoded = le_warehouse.transform([warehouse_id])[0]
        except Exception as e:
            print(f"Warehouse encoding error: {e}")
            return 1.0

        # Current time features
        now = datetime.now()

        # Prepare features
        features = np.array([[
            category_encoded,
            price,
            now.hour,
            now.isoweekday(),
            now.month,
            warehouse_encoded
        ]])

        # Predict
        prediction = model.predict(features)[0]

        return max(0.1, prediction)

    except Exception as e:
        print(f"Prediction error: {e}")
        import traceback
        traceback.print_exc()
        return 1.0


@app.route('/api/report', methods=['GET'])
def get_promotion_report():
    """
    API endpoint: Generates the promotion report and returns it in JSON format.
    The client will request this endpoint.
    """
    global latest_report, last_analysis_time, is_analyzing

    # Check if AI module initialized successfully
    if advisor is None:
        return jsonify({"error": "Advisor not initialized due to missing API Key or other startup error."}), 500

    # If cached report exists, return it immediately
    if latest_report is not None:
        return jsonify(latest_report)

    # If analysis is already running, inform the client to wait
    if is_analyzing:
        return jsonify({
            "status": "analyzing",
            "message": "AI analysis in progress, please wait..."
        }), 202  # 202 Accepted

    print("No cached report, generating new analysis...")
    # Start analysis task asynchronously
    Thread(target=run_ai_analysis, daemon=True).start()

    # Inform the client that the request has been accepted and analysis has started
    return jsonify({
        "status": "analyzing",
        "message": "First analysis started, please refresh in 10-15 seconds"
    }), 202


@app.route('/api/mongodb/logs', methods=['GET'])
def get_all_reports_api():
    """
    Retrieves all stored analysis reports from MongoDB.
    This route is essential for the analysis_reports.html frontend.
    """
    if db_handler is None:
        return jsonify({"error": "Database handler not initialized."}), 500
    try:
        reports = db_handler.get_all_reports()
        return jsonify(reports)
    except Exception as e:
        print(f"Error fetching MongoDB logs: {e}")
        return jsonify({"error": f"Failed to retrieve reports from database: {e}"}), 500

@app.route('/api/mongodb/delete/<id>', methods=['DELETE'])
def delete_report_api(id):
    """
    Deletes a specific analysis report by its MongoDB document ID.
    This route is essential for the analysis_reports.html frontend.
    """
    if db_handler is None:
        return jsonify({"error": "Database handler not initialized."}), 500
    try:
        success = db_handler.delete_report_by_id(id)
        if success:
            return jsonify({"message": f"Report {id} deleted successfully.", "success": True}), 200
        else:
            return jsonify({"message": f"Report with ID {id} not found.", "success": False}), 404
    except Exception as e:
        print(f"Error deleting MongoDB report {id}: {e}")
        return jsonify({"error": f"Failed to delete report: {e}"}), 500


@app.route('/api/charts/bar-top5', methods=['GET'])
def get_bar_chart_top5():
    chart = ChartDesign()
    bar = chart.generate_bar_chart_top5_slow_products()
    return bar

@app.route('/api/charts/scatter-price-days', methods=['GET'])
def get_scatter_chart():
    chart = ChartDesign()
    scatter = chart.generate_scatter_price_vs_days()
    return scatter

@app.route('/api/charts/pie-warehouse', methods=['GET'])
def get_pie_chart_warehouse():
    chart = ChartDesign()
    pie = chart.generate_pie_warehouse_distribution()
    return pie

# Machine Learning
@app.route('/api/predict-demand', methods=['POST'])
def predict_demand():
    """Predict order quantity"""
    data = request.json

    try:
        # Encode categorical features
        category_encoded = le_category.transform([data['product_category']])[0]
        warehouse_encoded = le_warehouse.transform([data['warehouse_id']])[0]

        # Prepare features
        features = np.array([[
            category_encoded,
            data['price'],
            data['order_hour'],
            data['order_day'],
            data['order_month'],
            warehouse_encoded
        ]])

        # Predict
        prediction = model.predict(features)[0]

        return jsonify({
            'predicted_quantity': round(prediction, 1),
            'status': 'success'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'model_loaded': True})


@app.route('/api/slow-moving-products', methods=['GET'])
def get_slow_moving_products_api():
    """
    Get top 5 slowest-selling products for ML pricing analysis
    """
    try:
        # get data from mysql
        mysql = SalesAnalyzer()
        products = mysql.get_slow_moving_products_ML()

        return jsonify({
            'status': 'success',
            'products': products,
            'count': len(products) if products else 0
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route("/Warehouse/")
def home():
    return send_file("index.html")

@app.route("/Warehouse/ai_suggestion.html")
def ai_suggestion():
    return send_file("ai_suggestion.html")

@app.route("/Warehouse/analysis_reports.html")
def analysis_report():
    return send_file("analysis_reports.html")

@app.route("/Warehouse/ml_pricing.html")
def ml_pricing():
    return send_file("ml_pricing.html")


@app.route('/api/pricing-analysis', methods=['POST'])
def pricing_analysis():
    """
    Analyze pricing strategy using pure ML prediction
    """
    data = request.json

    try:
        # 强制转换成float - 这是关键！
        current_price = float(data['current_price'])  # ← 加 float()
        monthly_sales = int(data.get('current_monthly_sales', 30))
        category = str(data['category'])  # ← 确保是字符串
        warehouse_id = str(data['warehouse_id'])  # ← 确保是字符串
        product_name = str(data['product_name'])

        if monthly_sales == 0:
            monthly_sales = 10  # 默认假设月销10件

        print(f"Converting types - price: {type(current_price)}, monthly_sales: {type(monthly_sales)}")

        scenarios = []

        # Current price
        current_qty = predict_quantity(category, current_price, warehouse_id)
        current_qty = float(current_qty)  # ← 确保是float

        current_revenue = current_price * current_qty * monthly_sales
        print(f"Current revenue calculation: {current_price} * {current_qty} * {monthly_sales} = {current_revenue}")

        scenarios.append({
            'discount_percent': 0,
            'price': round(float(current_price), 2),
            'predicted_qty_per_order': round(float(current_qty), 1),
            'estimated_monthly_sales': int(current_qty * monthly_sales),
            'estimated_monthly_revenue': round(float(current_revenue), 2),
            'revenue_change_percent': 0,
            'quantity_increase_percent': 0
        })

        # Test discounts: 10%, 20%, 30%, 40%
        for discount in [10, 20, 30, 40]:
            discounted_price = current_price * (1 - discount / 100)
            discounted_price = float(discounted_price)  # ← 确保是float

            predicted_qty = predict_quantity(category, discounted_price, warehouse_id)
            predicted_qty = float(predicted_qty)  # ← 确保是float

            estimated_sales = predicted_qty * monthly_sales
            estimated_revenue = discounted_price * estimated_sales

            revenue_change = ((estimated_revenue - current_revenue) / current_revenue) * 100
            qty_change = ((predicted_qty - current_qty) / current_qty) * 100

            scenarios.append({
                'discount_percent': discount,
                'price': round(float(discounted_price), 2),
                'predicted_qty_per_order': round(float(predicted_qty), 1),
                'estimated_monthly_sales': int(estimated_sales),
                'estimated_monthly_revenue': round(float(estimated_revenue), 2),
                'revenue_change_percent': round(float(revenue_change), 1),
                'quantity_increase_percent': round(float(qty_change), 1)
            })

        # Find optimal (max revenue)
        optimal_scenario = max(scenarios[1:], key=lambda x: x['estimated_monthly_revenue'])

        return jsonify({
            'status': 'success',
            'product_name': product_name,
            'current_scenario': scenarios[0],
            'price_scenarios': scenarios[1:],
            'optimal_scenario': optimal_scenario
        })

    except Exception as e:
        print(f"❌ Error in pricing analysis: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


if __name__ == '__main__':
    print("--- Starting Flask Server on http://127.0.0.1:5000 ---")

    # Initialize and start the daily scheduler
    # Assuming PromotionScheduler class is defined in Scheduler.py
    try:
        timer = PromotionScheduler()
        # Schedules the run_ai_analysis function to run periodically (e.g., daily)
        timer.schedule_daily_analysis(run_ai_analysis)
    except NameError:
        print("Warning: PromotionScheduler not initialized. Missing Scheduler.py?")
    except Exception as e:
        print(f"Error initializing scheduler: {e}")

    # Start Flask application
    app.run(debug=True, use_reloader=False)