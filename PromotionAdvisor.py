import os
from dotenv import load_dotenv  # load .env file
from google import genai
from google.genai.errors import APIError


class PromotionAdvisor:
    def __init__(self, env_file='config.env'):
        # Initialization class

        # load API
        load_dotenv('config.env')
        # get API KEY
        api_key = os.environ.get("GEMINI_API_KEY")

        # NOTE: For Canvas environment, api_key is often empty and handled by the runtime
        if not api_key:
            # Attempt to initialize client without explicit key for Canvas
            try:
                self.client = genai.Client()
            except Exception:
                raise EnvironmentError(
                    "Error：Can't initialize Gemini Client. Check if 'GEMINI_API_KEY' is set in config.env or if running in Canvas environment."
                )
        else:
            self.client = genai.Client(api_key=api_key)

        # model type: Gemimi-2.5-flash is free with few data
        self.model_name = "gemini-2.5-flash"

        print("PromotionAdvisor initialized and connected to Gemini API.")

    def get_suggestions(self, analysis_data: dict) -> str:
        """
        get data from database, use Gemini API get advisor, strictly filtering for 5 lowest Sell-Through Rate products.

        Args:
            analysis_data: the dict containing product information under the key 'slow_moving_products'

        Returns:
            return suggestions as a strict 5-row Markdown table
        """
        if not analysis_data:
            # DEBUG: Print the raw input data if it's None or empty, to diagnose SalesAnalyzer issue
            print("--- DEBUG: analysis_data is None or empty dict! ---")
            print(f"Raw data received: {analysis_data}")
            print("-------------------------------------------------")
            return (
                "| Product Name | Supply Name | Analysis | Promotional Strategy |\n"
                "| :---: | :---: | :---: | :---: |\n"
            )

        # Extract the actual list of products from the analysis dictionary
        product_data = analysis_data.get("slow_moving_products", [])

        if not product_data:
            # DEBUG: Print the full dictionary to see if other keys were present
            print("--- DEBUG: 'slow_moving_products' is empty! ---")
            print(f"Full dictionary received: {analysis_data}")
            print("-------------------------------------------")
            # Return a safe, empty table structure if product list is empty
            return ("NO DATA")
        # ---------------------------------------------------------------------------------

        # 1. Prepare Product Summary
        # Explicitly format the required fields for the prompt to guide the AI filtering.
        product_summary = "\n".join([
            # Adapt keys to match the user's provided data structure:
            f"- Name: {p.get('product_name', 'N/A')}, "
            f"Manufacturer: {p.get('manufacturer', 'N/A')}, " 
            f"Price: ${p.get('price', 0.00):.2f}, "
            f"Stock Remaining: {p.get('stock_quantity', 0)}, "
            # Calculate Units Sold (supply_quantity - stock_quantity)
            f"Units Sold: {p.get('supply_quantity', 0) - p.get('stock_quantity', 0)}, "
            # Use the 'sell_through_rate' Decimal field directly
            f"Sell-Through STR: {p.get('sell_through_rate', '0.00')}%, "
            # Historical promo data is missing in the raw product dictionary items, using placeholders/assumptions for the AI:
            f"Historical Promo Type: {'None'}, Historical Promo Lift: {'0%'}"
            for p in product_data
        ])

        total_products = len(product_data)

        # 2. Define the STICKY prompt (Combining System & User Query with strict constraints)
        # Uses the highly constrained English prompt to enforce filtering and output format.
        strict_prompt = (
            "You are a professional retail analyst. Your task is to perform an in-depth analysis and provide detailed, actionable promotional suggestions **only for the 5 products with the lowest Sell-Through Rate (STR)**, based on the provided product inventory and sales data.\n\n"

            "--- Core Task and Constraints (Must be **STRICTLY ENFORCED**) ---\n"
            "1. **Data Filtering (Highest Priority):** From all products, you **must strictly** select the **5 products with the lowest Sell-Through Rate** as the final subjects for analysis; **do not analyze any other products**.\n"
            "2. **Output Format (Highest Priority):** The final output must be **ONLY a Markdown table**. **NO explanatory text, summaries, titles, or Markdown code fences (```) are allowed before or after the table**. The table must contain exactly 5 rows of suggestions.\n"
            "3. **Table Structure:** The table must contain and **ONLY contain** the following four columns, with names matching exactly: 'Product Name', 'Supply Name', 'Analysis', 'Promotional Strategy'.\n"

            "4. **Analysis Content Requirements:**\n"
            "   - The analysis must be deep and exhaustive, aimed at explaining the root causes of sluggish sales.\n"
            "   - **NOTE on Historical Data:** The Historical Promotion Type and Lift data is **missing** (marked as 'None'/'0%'). The analysis should, therefore, focus purely on the extremely low STR, high stock quantity, and competitive pricing issues to determine an effective *first* major clearance strategy.\n"
            "   - Identify the fundamental reasons for inventory accumulation (e.g., pricing too high, seasonality mismatch, competitive environment).\n"

            "5. **Promotional Strategy Content Requirements:**\n"
            "   - The strategy must be specific and actionable, **avoiding vague terms**.\n"
            "   - Recommend a **strong clearance plan** to maximize inventory clearance immediately.\n"
            "   - Detail the mechanism and specific execution details of the strategy (e.g., direct 30% off, Buy One Get One Free, 2-week window, exclusive live stream campaign).\n\n"

            f"**Product Data (Total {total_products} items):**\n"
            f"{product_summary}\n\n"
            "**START YOUR RESPONSE NOW. REMEMBER: ONLY A 5-ROW MARKDOWN TABLE IS ALLOWED.**"
        )

        print(f"\n--- Sending request to {self.model_name}... ---")

        # --- API Call and Return Logic ---
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=strict_prompt
            )

            raw_text = response.text.strip()

            lines = raw_text.split('\n')
            cleaned_lines = []
            for line in lines:
                stripped_line = line.strip()
                is_table_row = stripped_line.startswith('|') and stripped_line.endswith('|')
                is_separator = '---' in stripped_line

                if is_table_row:
                    if not stripped_line.startswith('```'):
                        cleaned_lines.append(stripped_line)

                elif is_separator and stripped_line.startswith('|') and stripped_line.endswith('|'):
                    cleaned_lines.append(stripped_line)

            # 3. Join the cleaned lines back into a single string
            return "\n".join(cleaned_lines)

        except APIError as e:

            return (
                "| Product Name | Supply Name | Analysis | Promotional Strategy |\n"
                "| :---: | :---: | :---: | :---: |\n"
                f"| API Error | N/A | API Active fail ({e.status_code})。 |"
            )
        except Exception as e:

            return (
                "| Product Name | Supply Name | Analysis | Promotional Strategy |\n"
                "| :---: | :---: | :---: | :---: |\n"
                f"| Runtime Error | N/A | error：{e} |"
            )