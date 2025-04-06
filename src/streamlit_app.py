import streamlit as st
import pandas as pd
import sqlite3
import utils.db_helper as db_helper
import altair as alt

# Path to SQLite Sales database
DB_PATH = "data/sales_database.db"

st.set_page_config(layout="wide")

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

# LOGIN/REGISTRATION
if not st.session_state.logged_in:
    # Login form
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.title("Sales Dashboard Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login")

    # Registration form
    col4, col5, col6 = st.columns([1, 1, 1])
    with col5:
        st.write("### Create New Account")
        with st.form("registration_form"):
            new_username = st.text_input("New Username")
            new_password = st.text_input("New Password", type="password")
            register_button = st.form_submit_button("Register")

    # Login button logic
    if login_button:
        if db_helper.validate_user_login(DB_PATH, username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid username or password.")

    # Registration button logic
    if register_button:
        try:
            connection = sqlite3.connect(DB_PATH)
            cursor = connection.cursor()

            # Hash password before storing it
            hashed_password = db_helper.hash_password(new_password)

            # Insert new user into database
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (new_username, hashed_password))
            connection.commit()
            connection.close()

            st.success("Registration successful! You can now log in.")
        except sqlite3.IntegrityError:
            st.error("Username already exists. Please choose a different username.")
        except Exception as e:
            st.error(f"Error during registration: {e}")

# If user is logged in
# MAIN DASHBOARD
else:
    st.sidebar.write(f"Logged in as: {st.session_state.username}")
    logout_button = st.sidebar.button("Logout")

    # Logout button logic
    if logout_button:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

    # Display dashboard
    st.title("Sales Dashboard")
    db_helper.create_sales_database(DB_PATH)
    query = "SELECT * FROM sales_data"
    data = db_helper.get_db_data(DB_PATH, query)

    # Convert Close Date to datetime
    data['Close Date'] = pd.to_datetime(data['Close Date'])

    # Convert dollar values to numeric
    dollar_columns = ['Winning Bid', 'Net Sales', 'Expenses']
    for col in dollar_columns:
        data[col] = data[col].replace('[\$,]', '', regex=True).astype(float)
    data.rename(columns={col: f"{col} (USD)" for col in dollar_columns}, inplace=True)

    # Sort departments and filter by department
    departments = sorted(data['Department'].unique())
    selected_all = st.sidebar.checkbox("Select All Departments", value=True)

    if selected_all:
        selected_departments = departments
    else:
        selected_departments = st.sidebar.multiselect(
            "Select Department(s)", 
            options=departments, 
            default=departments,
        )

    # Filter by date range using slider
    min_date = data['Close Date'].min().date()
    max_date = data['Close Date'].max().date()
    start_date, end_date = st.sidebar.slider(
        "Select Date Range",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="MM/DD/YYYY"
    )

    # Add checkbox to toggle outlier removal
    remove_outliers = st.sidebar.checkbox("Remove Outliers", value=False)

    # Apply filters
    filtered_data = data[
        (data['Department'].isin(selected_departments)) &
        (data['Close Date'] >= pd.to_datetime(start_date)) &
        (data['Close Date'] <= pd.to_datetime(end_date)) &
        (data['Auction ID'].notna() if not remove_outliers else ~data['Auction ID'].isin([82027, 92549]))
    ]

    # Choose columns to display
    columns_to_display = ['Auction Title', 'Department', 'Close Date', 'Winning Bid (USD)', 'Fund', 'Net Sales (USD)']

    # Create two columns for top two quadrants
    col1, col2 = st.columns(2)

    # Display filtered data
    with col1:
        st.write("### Filtered Data")
        st.dataframe(filtered_data[columns_to_display])

    # Calculate metrics
    total_sales = filtered_data['Net Sales (USD)'].sum()
    total_expenses = filtered_data['Expenses (USD)'].sum()
    net_profit = total_sales - total_expenses

    # Group by department and sort by descending Net Sales
    sales_by_department = filtered_data.groupby('Department')['Net Sales (USD)'].sum().reset_index()
    sales_by_department = sales_by_department.sort_values(by='Net Sales (USD)', ascending=False)

    # Create a pie chart
    pie_chart = alt.Chart(sales_by_department).mark_arc().encode(
        theta=alt.Theta(field='Net Sales (USD)', type='quantitative'),
        color=alt.Color(field='Department', type='nominal', sort=sales_by_department['Department'].tolist()),
        tooltip=['Department', 'Net Sales (USD)']
    ).properties(
        title="Sales by Department"
    )

    # Ensure Close Date is in datetime format and set it as the index
    filtered_data['Close Date'] = pd.to_datetime(filtered_data['Close Date'])
    filtered_data.set_index('Close Date', inplace=True)

    # Group by month and calculate total sales and count of sales
    monthly_sales = filtered_data.resample('ME').agg({
        'Net Sales (USD)': 'sum',
        'Auction ID': 'count'
    }).reset_index()

    # Rename columns
    monthly_sales.rename(columns={'Auction ID': 'Sales Count'}, inplace=True)

    # Ensure there is at least one row of data
    if monthly_sales.empty:
        monthly_sales = pd.DataFrame({
            'Close Date': [pd.Timestamp('2000-01-01')],
            'Net Sales (USD)': [0.0],
            'Sales Count': [0]
        })

    # Create dual-axis chart
    line_chart_sales = alt.Chart(monthly_sales).mark_line(color='blue').encode(
        x='Close Date:T',
        y=alt.Y('Net Sales (USD):Q', scale=alt.Scale(domain=[0, monthly_sales['Net Sales (USD)'].max()]), title='Net Sales (USD)', axis=alt.Axis(titleColor='blue'))
    )
    line_chart_count = alt.Chart(monthly_sales).mark_line(color='orange').encode(
        x='Close Date:T',
        y=alt.Y('Sales Count:Q', scale=alt.Scale(domain=[0, monthly_sales['Sales Count'].max()]), title='Sales Count', axis=alt.Axis(titleColor='orange'))
    )

    # Combine two charts
    dual_axis_chart = alt.layer(line_chart_sales, line_chart_count).resolve_scale(
        y='independent'
    )

    # Display pie chart
    with col2:
        st.write("### Sales by Department")
        st.altair_chart(pie_chart, use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Auctions", len(filtered_data))

    with col2:
        st.metric("Median Winning Bid", f"${filtered_data['Winning Bid (USD)'].median():,.2f}")

    with col3:
        st.metric("Net Profit", f"${net_profit:,.2f}")

    with col4:
        st.metric("Average Winning Bid", f"${filtered_data['Winning Bid (USD)'].mean():,.2f}")

    # Display dual-axis chart
    st.write("### Monthly Sales Trend with Sales Count")
    st.altair_chart(dual_axis_chart, use_container_width=True)




