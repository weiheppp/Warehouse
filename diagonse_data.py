import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('warehouse_data.csv')

print("="*60)
print("Data Diagnosis")
print("="*60)

# 1. 检查订单数量分布
print("\n1. Order Quantity Distribution:")
print(df['orderquantity'].value_counts().sort_index())
print(f"\nMean: {df['orderquantity'].mean():.2f}")
print(f"Std: {df['orderquantity'].std():.2f}")
print(f"Min: {df['orderquantity'].min()}")
print(f"Max: {df['orderquantity'].max()}")

# 2. 订单数量的直方图
plt.figure(figsize=(10, 6))
plt.hist(df['orderquantity'], bins=20, edgecolor='black')
plt.xlabel('Order Quantity')
plt.ylabel('Frequency')
plt.title('Distribution of Order Quantity')
plt.savefig('orderquantity_distribution.png')
print("\n✓ Saved orderquantity_distribution.png")

# 3. 检查价格和订单数量的关系
plt.figure(figsize=(10, 6))
plt.scatter(df['price'], df['orderquantity'], alpha=0.3)
plt.xlabel('Price')
plt.ylabel('Order Quantity')
plt.title('Price vs Order Quantity')
plt.savefig('price_vs_quantity.png')
print("✓ Saved price_vs_quantity.png")

# 4. 按类别统计
print("\n2. Order Quantity by Category:")
category_stats = df.groupby('product_category')['orderquantity'].agg(['mean', 'std', 'min', 'max'])
print(category_stats)

# 5. 按时间统计
print("\n3. Order Quantity by Hour:")
hour_stats = df.groupby('order_hour')['orderquantity'].agg(['mean', 'count'])
print(hour_stats)

print("\n" + "="*60)
print("Diagnosis Complete!")
print("="*60)