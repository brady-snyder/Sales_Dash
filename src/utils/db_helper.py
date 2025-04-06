import sqlite3
import pandas as pd
import bcrypt

def create_sales_database(db_path):
    """
    Create a SQLite database and populate it with data from a hardcoded CSV file
    Args:
        db_path (str): Path to SQLite database
    """
    try:
        # Load data from CSV
        csv_file_path = 'data/eBid_Monthly_Sales.csv'
        data = pd.read_csv(csv_file_path)

        # Strip whitespace from column names
        data.columns = data.columns.str.strip()

        # Create/Connect to SQLite database
        connection = sqlite3.connect(db_path)

        # Create a new table with data
        data.to_sql('sales_data', connection, if_exists='replace', index=False)

        # Commit changes and close connection
        connection.commit()
        connection.close()
        print(f"Database created successfully at {db_path}")

    except Exception as e:
        print(f"Error creating database: {e}")

def get_db_data(db_path, query):
    """
    Get data from SQLite database using SQL query
    Args:
        db_path (str): Path to SQLite database
        query (str): SQL query
    Returns:
        pd.DataFrame: DataFrame containing result
    """
    # Connect to SQLite database
    connection = sqlite3.connect(db_path)

    # Get data using query
    data = pd.read_sql_query(query, connection)

    # Close connection
    connection.close()

    return data

def validate_user_login(db_path, username, password):
    """
    Validate user login credentials with hashed passwords
    Args:
        db_path (str): Path to SQLite database
        username (str): Username
        password (str): Password
    Returns:
        bool: True if login is valid, False otherwise
    """
    try:
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        # Query to get hashed password for given username
        cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()

        connection.close()

        if result:
            hashed_password = result[0]
            # Verify provided password against hashed password
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        return False

    except Exception as e:
        print(f"Error validating login: {e}")
        return False
    
def hash_password(password):
    """
    Hash a plain-text password using bcrypt
    Args:
        password (str): Plain-text password
    Returns:
        str: The hashed password
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')