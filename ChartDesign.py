import warnings
warnings.filterwarnings('ignore', message='.*urllib3 v2.*')

import matplotlib
matplotlib.use('Agg')  # no gui mode
import matplotlib.pyplot as plt
import io
import base64
from matplotlib.colors import LinearSegmentedColormap

from SalesAnalyzer import SalesAnalyzer

# global
# Apple-style grey
DARK_GRAY = '#4A5568'
MEDIUM_GRAY = '#718096'
LIGHT_GRAY = '#A0AEC0'
VERY_LIGHT_GRAY = '#CBD5E0'
BACKGROUND = '#F7FAFC'
ACCENT = '#2D3748'

# various gray
GRAY_COLORS = ['#E2E8F0', '#A0AEC0', '#718096']

# White background + grid lines
plt.style.use('seaborn-v0_8-whitegrid')
# Set the default font for the chart:
# Prefer Arial  Alternatives: Helvetica / DejaVu Sans
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
# Make the negative signs on the coordinate axes display correctly, instead of as gibberish.
plt.rcParams['axes.unicode_minus'] = False
# Set the background of the coordinate area to pure white.
plt.rcParams['axes.facecolor'] = '#FFFFFF'
# Set the background of the entire image to pure white
plt.rcParams['figure.facecolor'] = '#FFFFFF'
# Set the axis border color (light gray).
plt.rcParams['axes.edgecolor'] = '#E2E8F0'
# Set the width of the coordinate axis border lines to 1 (the default is usually 0.8).
plt.rcParams['axes.linewidth'] = 1
# Set the gridline color to a very light gray.
plt.rcParams['grid.color'] = '#F7FAFC'
# Set the grid line width to 0.8 to make it softer and less obvious.
plt.rcParams['grid.linewidth'] = 0.8

class ChartDesign:

    def convert_to_base64(self, fig):
        # change chart to base64 which can be used by html
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close(fig)
        return f"data:image/png;base64,{image_base64}"

    def generate_bar_chart_top5_slow_products(self):
        sql = SalesAnalyzer()

        data = sql.top5_slow_products()

        if not data:
            return {"error": "No data found"}

        # extra data
        products = [row['product_name'] for row in data]
        rates = [float(row['sell_through_rate']) for row in data]

        # create bar chart
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('white')
        bars = ax.barh(products, rates, color=DARK_GRAY, edgecolor='none', height=0.6)

        # add value
        ax.set_xlabel('Sell-Through Rate (%)', fontsize=11,
                      fontweight='normal', color = MEDIUM_GRAY)
        ax.set_title('Top 5 Products with Lowest Sell-Through Rates',
                     fontsize=13, fontweight='600', pad=15, color = ACCENT, loc = 'left')

        # Remove border
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(VERY_LIGHT_GRAY)
        ax.spines['bottom'].set_color(VERY_LIGHT_GRAY)

        # grid very light
        ax.grid(axis='x', alpha=0.2, linestyle='-', linewidth=0.5, color=VERY_LIGHT_GRAY)
        ax.set_axisbelow(True)

        # y label type
        ax.tick_params(axis='y', labelsize=10, colors=MEDIUM_GRAY, length=0)
        ax.tick_params(axis='x', labelsize=9, colors=LIGHT_GRAY)

        ax.invert_yaxis()

        plt.tight_layout()

        # covert to base64
        image_base64 = self.convert_to_base64(fig)

        #save at root
        img_data = image_base64.split(',')[1]
        with open("barchart.png", 'wb') as f:
           f.write(base64.b64decode(img_data))
        print("barchart.png saved success!")

        return {
            "success": True,
            "chart_type": "bar",
            "title": "Top 5 Products with Lowest Sell-Through Rates",
            "image": image_base64,
            "data_points": len(data),
            "business_insight": "Identifies the most underperforming products requiring immediate promotional action"
        }

    def generate_scatter_price_vs_days(self):
        sql = SalesAnalyzer()

        data = sql.price_vs_days()

        if not data:
            return {"error": "No data found"}

        # extra data
        prices = [float(row['price']) for row in data]
        days = [row['days_in_stock'] for row in data]

        # create scatter chart
        fig, ax = plt.subplots(figsize=(10, 7))
        fig.patch.set_facecolor('white')

        # set various gray
        custom_cmap = LinearSegmentedColormap.from_list('modern_gray', GRAY_COLORS, N = 100)


        # accordong to days the color will chagne from yellow to red
        scatter = ax.scatter(prices, days,
                             c=days,
                             cmap=custom_cmap,
                             s=80,
                             alpha=0.6,
                             edgecolors=MEDIUM_GRAY,
                             linewidths=0.5,
                             label = 'Product Data')

        # the color represent the days
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Days in Stock', fontsize=10, color = MEDIUM_GRAY, rotation = 270, labelpad = 20)
        cbar.ax.tick_params(color = LIGHT_GRAY, labelsize = 9)
        cbar.outline.set_edgecolor(VERY_LIGHT_GRAY)


        ax.set_xlabel('Product Price ($)', fontsize=11, fontweight='normal', color = MEDIUM_GRAY)
        ax.set_ylabel('Days in Stock', fontsize=11, fontweight='normal', color = MEDIUM_GRAY)
        ax.set_title('Price vs Days in Stock - Correlation Analysis',
                     fontsize=13, fontweight='600', pad=15, loc = 'left', color = ACCENT)

        # remove boarder
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(VERY_LIGHT_GRAY)
        ax.spines['bottom'].set_color(VERY_LIGHT_GRAY)

        ax.grid(True, alpha=0.15, linestyle='-', linewidth = 0.5, color = VERY_LIGHT_GRAY)
        ax.set_axisbelow(True)

        ax.tick_params(color = LIGHT_GRAY, labelsize = 9)

        # manual
        ax.legend(loc='upper right', fontsize=9, frameon = True, facecolor = 'white',
                  edgecolor = VERY_LIGHT_GRAY, framealpha = 0.95)

        plt.tight_layout()

        # convert to base64
        image_base64 = self.convert_to_base64(fig)

        # save chart at root
        img_data = image_base64.split(',')[1]
        with open("scatterchart.png", 'wb') as f:
            f.write(base64.b64decode(img_data))
        print("scatterchart.png saved success")

        return {
            "success": True,
            "chart_type": "scatter",
            "title": "Price vs Days in Stock Analysis",
            "image": image_base64,
            "data_points": len(data),
            "business_insight": "Reveals if higher-priced products tend to stay in inventory longer"
        }

    def generate_pie_warehouse_distribution(self):
        sql = SalesAnalyzer()

        data = sql.warehouse_distribution()

        if not data:
            return {"error": "No data found"}

        # extra data
        locations = [f"{row['location']}\n({row['warehouse_id']})" for row in data]
        stocks = [row['total_stock'] for row in data]

        # create pie chart
        fig, ax = plt.subplots(figsize=(10, 8))
        fig.patch.set_facecolor('white')

        APPLE_PIE_COLORS = [
             '#007AFF',  # iOS blue
             '#E5E5EA',  # light gray
             '#C7C7CC',  # medium gray
             '#AEAEB2',  # dark gray
             '#8E8E93',  # very dark gray
             '#636366',  # more dark gray
             '#48484A',  # more more dark gary
             '#3A3A3C'   # neraly black
        ]

        # draw pie
        wedges, texts, autotexts = ax.pie(
            stocks,
            labels=locations,
            autopct='%1.1f%%',
            startangle=90,
            colors= APPLE_PIE_COLORS[:len(locations)],
            explode=[0.05] * len(locations),
            shadow=False,
            textprops={'fontsize': 11, 'fontweight': '500'}
        )

        # label type
        for text in texts:
            text.set_color(DARK_GRAY)
            text.set_fontsize(11)
            text.set_fontweight('500')

        # letter type
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(12)
            autotext.set_fontweight('700')

        ax.set_title('Inventory Distribution Across Warehouses',
                     fontsize=14, fontweight='600', pad=20,
                     color = ACCENT, loc = 'left')

        # document
        ax.legend(
            [f"{loc}: {stock:,} units" for loc, stock in zip(locations, stocks)],
            loc='center left',
            bbox_to_anchor=(1, 0.5),
            fontsize=10,
            frameon = False,  # no boarder
            labelcolor = MEDIUM_GRAY
        )

        plt.tight_layout()

        # base64
        image_base64 = self.convert_to_base64(fig)

        # save chart at root
        img_data = image_base64.split(',')[1]
        with open("piechart.png", 'wb') as f:
           f.write(base64.b64decode(img_data))
        print("piechart.png saved success!")

        return {
            "success": True,
            "chart_type": "pie",
            "title": "Warehouse Inventory Distribution",
            "image": image_base64,
            "data_points": len(data),
            "business_insight": "Identifies warehouses with highest inventory pressure for rebalancing"
        }