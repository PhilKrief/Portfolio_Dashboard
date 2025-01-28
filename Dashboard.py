import streamlit as st
import pandas as pd
import requests
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Retrieve the API key
API_KEY = os.getenv("API_KEY")

def get_stock_price(ticker):
    """Fetch the current, yesterday's, and previous quarter's closing prices."""
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if "historical" in data:
        # Extract historical data
        prices = pd.DataFrame(data["historical"])
        prices["date"] = pd.to_datetime(prices["date"])
        prices = prices.sort_values("date").reset_index(drop=True)

        # Current and yesterday's close
        current_close = prices.iloc[-1]["close"]
        yesterday_close = prices.iloc[-2]["close"]

        # Find the previous quarter's last trading day
        today = datetime.today()
        current_quarter_start = (today.month - 1) // 3 * 3 + 1
        previous_quarter_end = datetime(today.year, current_quarter_start, 1) - timedelta(days=1)

        # Filter for previous quarter's close
        previous_quarter_prices = prices[prices["date"] <= previous_quarter_end]
        if not previous_quarter_prices.empty:
            previous_quarter_close = previous_quarter_prices.iloc[-1]["close"]
        else:
            previous_quarter_close = None

        return current_close, yesterday_close, previous_quarter_close

    return None, None, None

def get_sp500_performance():
    """Fetch SPY performance for the current quarter."""
    spy_current, spy_yesterday, spy_previous_quarter = get_stock_price("SPY")
    if spy_current and spy_previous_quarter:
        spy_qtd_return = (spy_current - spy_previous_quarter) / spy_previous_quarter * 100
        spy_daily_return = (spy_current - spy_yesterday) / spy_yesterday * 100
        return spy_qtd_return, spy_daily_return
    return None, None

def calculate_portfolio_performance(df):
    """Calculate portfolio performance based on weights and stock performance."""
    portfolio_qtd_return = np.sum(df["Weight (%)"] * df["Quarterly Return (%)"])/100
    portfolio_daily_return = np.sum(df["Weight (%)"] * df["Day Gain (%)"])/100
    return portfolio_qtd_return, portfolio_daily_return

@st.cache_data
def load_portfolio_from_file(file):
    """
    Load portfolio data from the uploaded or default file.
    """
    portfolio = pd.read_csv(file)
    portfolio.columns = ["Tickers", "Weights"]
    portfolio["Tickers"] = portfolio["Tickers"].str.split("_").str[0]  # Extract tickers before "_"
    portfolio["Weights"] = portfolio["Weights"] * 100  # Convert weights to percentages
    return portfolio

def authenticate_and_load_portfolio(password: str, stored_password: str):
    """
    Authenticate the user and determine the file to load based on the provided password.
    """
    if password == stored_password:
        # Automatically load the file from the folder
        try:
            return "portfolio_weights_current.csv", "File loaded from folder."
        except FileNotFoundError:
            return None, "Default portfolio file not found. Please upload a file."
    else:
        # Prompt the user to upload a file
        uploaded_file = st.file_uploader("Upload Portfolio Weights File (CSV)", type=["csv"])
        if uploaded_file:
            return uploaded_file, "File uploaded successfully."
    return None, "Please provide a valid password or upload a file."

# Main Dashboard
st.title("Portfolio Dashboard")
st.subheader("Current Quarter Performance")

# Password input
stored_password = os.getenv("STORED_PASSWORD")  # Replace with your secure password
password = st.text_input("Enter Password (optional):", type="password")

# Authenticate and determine the file
file_to_load, message = authenticate_and_load_portfolio(password, stored_password)
st.info(message)

# Load the portfolio if a file is determined
if file_to_load:
    portfolio = load_portfolio_from_file(file_to_load)

    # Fetch stock prices and calculate returns
    performance_data = []
    for _, row in portfolio.iterrows():
        ticker = row["Tickers"]
        current_price, yesterday_price, previous_quarter_price = get_stock_price(ticker)
        if current_price and yesterday_price and previous_quarter_price:
            quarterly_return = (current_price - previous_quarter_price) / previous_quarter_price * 100
            day_gain = (current_price - yesterday_price) / yesterday_price * 100
            performance_data.append(
                (
                    ticker,
                    row["Weights"],
                    current_price,
                    yesterday_price,
                    previous_quarter_price,
                    quarterly_return,
                    day_gain,
                )
            )

    # Create Performance Table
    performance_df = pd.DataFrame(
        performance_data,
        columns=[
            "Ticker",
            "Weight (%)",
            "Current Price",
            "Yesterday's Close",
            "Previous Quarter Price",
            "Quarterly Return (%)",
            "Day Gain (%)",
        ]
    )
    performance_df["Performance Contribution (%)"] = (
        performance_df["Weight (%)"] * performance_df["Quarterly Return (%)"] / 100
    )
    
    # Round all numerical values to 2 decimals
    performance_df = performance_df.round(2)
    
    # Calculate SPY and Portfolio QTD and Daily Returns
    spy_qtd_return, spy_daily_return = get_sp500_performance()
    portfolio_qtd_return, portfolio_daily_return = calculate_portfolio_performance(performance_df)

    # Calculate Delta
    qtd_delta = portfolio_qtd_return - spy_qtd_return
    daily_delta = portfolio_daily_return - spy_daily_return

    # Create a DataFrame for the summary table
    summary_table = pd.DataFrame({
        "Metric": ["QTD Return", "Daily Return"],
        "Portfolio": [f"{portfolio_qtd_return:.2f}%", f"{portfolio_daily_return:.2f}%"],
        "SPY": [f"{spy_qtd_return:.2f}%", f"{spy_daily_return:.2f}%"],
        "Delta": [f"{qtd_delta:.2f}%", f"{daily_delta:.2f}%"]
    })

    # Display the Summary Table
    st.write("### Performance Summary Table")
    st.table(summary_table)

    # Display the Portfolio Performance Table
    st.write("### Portfolio Performance Table")
    st.dataframe(performance_df)

    # Add a note for the deep dive page
    st.write("Go to the **Stock Deep Dive** page for stock-specific analysis.")
