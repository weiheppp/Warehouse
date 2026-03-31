import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import joblib
import os

from ML_extract_data import ml_data

# Create models folder if not exists
if not os.path.exists('models'):
    os.makedirs('models')
    print("✓ Created 'models' folder")

# Load data from CSV
# Load data from CSV or database
if os.path.exists('warehouse_data.csv'):
    print("\n✓ Found existing CSV file, loading...")
    df = pd.read_csv('warehouse_data.csv')
else:
    ml = ml_data()
    df = ml.extract()
    print("loading data from MySQL")

# Feature Engineering
print("\n" + "="*60)
print("Feature Engineering...")
print("="*60)

# Encode categorical variables
le_category = LabelEncoder()
le_warehouse = LabelEncoder()

df['product_category_encoded'] = le_category.fit_transform(df['product_category'])
df['warehouse_encoded'] = le_warehouse.fit_transform(df['warehouse_id'])

# Select features for training
feature_columns = [
    'product_category_encoded',
    'price',
    'order_hour',
    'order_day',
    'order_month',
    'warehouse_encoded'
]

X = df[feature_columns]
y = df['orderquantity']


# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train model
print("\n" + "="*60)
print("Training Random Forest model...")
print("="*60)

model = RandomForestRegressor(
    n_estimators=100,
    max_depth=12,
    min_samples_split=20,
    min_samples_leaf=10,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)
print("✓ Model trained successfully!")

# Evaluate model
print("\n" + "="*60)
print("Model Evaluation:")
print("="*60)

y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)

train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
train_r2 = r2_score(y_train, y_pred_train)
test_r2 = r2_score(y_test, y_pred_test)
test_mae = mean_absolute_error(y_test, y_pred_test)

print(f"Training RMSE: {train_rmse:.3f}")
print(f"Test RMSE: {test_rmse:.3f}")
print(f"Training R²: {train_r2:.3f}")
print(f"Test R²: {test_r2:.3f}")
print(f"Test MAE: {test_mae:.3f}")

# Feature importance
print("\n" + "="*60)
print("Feature Importance:")
print("="*60)
feature_importance = pd.DataFrame({
    'feature': feature_columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print(feature_importance)

# Save model and encoders
print("\n" + "="*60)
print("Saving model...")
print("="*60)

joblib.dump(model, 'models/demand_forecast_model.pkl', compress=3)
joblib.dump(le_category, 'models/category_encoder.pkl')
joblib.dump(le_warehouse, 'models/warehouse_encoder.pkl')
joblib.dump(feature_columns, 'models/feature_columns.pkl')

# Check model file size
model_size = os.path.getsize('models/demand_forecast_model.pkl') / (1024 * 1024)
print(f"✓ Model saved: {model_size:.2f} MB")
print("✓ Encoders saved")

print("\n" + "="*60)
print("Step 2 Complete!")
print("="*60)
print("\nNext: Create Flask API for predictions")