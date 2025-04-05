import sqlite3
import pandas as pd

# Load data file
df = pd.read_csv('eBid_Monthly_Sales.csv')

# Clean data
df.columns = df.columns.str.strip()

# Create/connect to database
connection = sqlite3.connect('sales_database.db')

# Load data file to SQLite
df.to_sql('sales_database', connection, if_exists='replace')

# Close connection
connection.close()