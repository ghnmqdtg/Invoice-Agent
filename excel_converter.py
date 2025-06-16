import pandas as pd

# Convert `product_dataset.xlsx` to `shared/product_db.csv`
df = pd.read_excel("./DB/product_dataset.xlsx")
# Update the column names to match the expected format
df.columns = ['product_id', 'product_name', 'unit', 'currency']
# Remove duplicate rows
df = df.drop_duplicates()
# Save to CSV
df.to_csv("./python-scripts/shared/product_db.csv", index=False)

print("Conversion complete!")