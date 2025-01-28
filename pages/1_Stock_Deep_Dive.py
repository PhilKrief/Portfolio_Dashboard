import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Retrieve the API key
API_KEY = os.getenv("API_KEY")

# Helper functions
def get_historical_prices(ticker):
    """Fetch historical prices for the given ticker."""
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    if "historical" in data:
        prices = pd.DataFrame(data["historical"])
        prices["date"] = pd.to_datetime(prices["date"])
        prices = prices.sort_values("date")
        return prices
    return None

def get_profile(ticker):
    """Fetch the profile information for the given ticker."""
    url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]  # Assume the first result contains the profile info
    return None

def calculate_returns(prices):
    """Calculate day return and QTD return."""
    if prices is not None and not prices.empty:
        current_price = prices.iloc[-1]["close"]
        yesterday_price = prices.iloc[-2]["close"]
        qtd_start_date = datetime(datetime.today().year, (datetime.today().month - 1) // 3 * 3 + 1, 1)- timedelta(days=1)
 
        qtd_prices = prices[prices["date"] >= qtd_start_date]
        qtd_start_price = qtd_prices.iloc[0]["close"] if not qtd_prices.empty else None

        day_return = (current_price - yesterday_price) / yesterday_price * 100 if yesterday_price else None
        qtd_return = (current_price - qtd_start_price) / qtd_start_price * 100 if qtd_start_price else None

        return day_return, qtd_return
    return None, None

def rebase_prices(prices):
    """Rebase prices to calculate cumulative returns."""
    return (prices / prices.iloc[0] - 1) * 100

def get_financial_statements(ticker, statement_type):
    """Fetch quarterly financial statements for the given ticker."""
    url = f"https://financialmodelingprep.com/api/v3/{statement_type}/{ticker}?period=quarter&apikey={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data:
            return pd.DataFrame(data)
    return None

def calculate_financial_metrics(ticker):
    """Calculate financial metrics for the given ticker."""
    # Fetch financial data
    income_statement = get_financial_statements(ticker, "income-statement")
    cashflow_statement = get_financial_statements(ticker, "cash-flow-statement")

    if income_statement is not None and cashflow_statement is not None:
        # Flip the dataframes to get chronological order
        income_statement = income_statement.iloc[::-1].reset_index(drop=True)
        cashflow_statement = cashflow_statement.iloc[::-1].reset_index(drop=True)

        # Current quarter metrics
        revenue = income_statement.iloc[-1]["revenue"]
        gross_profit = income_statement.iloc[-1]["grossProfit"]
        net_income = income_statement.iloc[-1]["netIncome"]
        weighted_avg_shares = income_statement.iloc[-1]["weightedAverageShsOut"]
        eps = income_statement.iloc[-1]["eps"]  # Regular EPS (not diluted)

        free_cash_flow = cashflow_statement.iloc[-1]["freeCashFlow"]
        fcf_per_share = free_cash_flow / weighted_avg_shares if weighted_avg_shares else None

        gross_margin = gross_profit / revenue if revenue else None
        net_income_margin = net_income / revenue if revenue else None

        # TTM metrics
        ttm_revenue = income_statement["revenue"].iloc[-4:].sum()
        ttm_gross_profit = income_statement["grossProfit"].iloc[-4:].sum()
        ttm_net_income = income_statement["netIncome"].iloc[-4:].sum()
        ttm_free_cash_flow = cashflow_statement["freeCashFlow"].iloc[-4:].sum()
        ttm_fcf_per_share = (
            ttm_free_cash_flow / income_statement["weightedAverageShsOut"].iloc[-4:].mean()
            if weighted_avg_shares
            else None
        )
        ttm_eps = income_statement["eps"].iloc[-4:].sum()

        # YoY Growth Metrics
        yoy_revenue_growth = (
            revenue / income_statement.iloc[-5]["revenue"] - 1
            if income_statement.shape[0] > 4 and income_statement.iloc[-5]["revenue"]
            else None
        )
        yoy_eps_growth = (
            eps / income_statement.iloc[-5]["eps"] - 1
            if income_statement.shape[0] > 4 and income_statement.iloc[-5]["eps"]
            else None
        )
        yoy_fcf_growth = (
            free_cash_flow / cashflow_statement.iloc[-5]["freeCashFlow"] - 1
            if cashflow_statement.shape[0] > 4 and cashflow_statement.iloc[-5]["freeCashFlow"]
            else None
        )

        # Build the metrics table
        metrics_data = {
            "Metric": [
                "Revenue",
                "Gross Profit",
                "Net Income",
                "Gross Margin",
                "Net Income Margin",
                "Free Cash Flow",
                "FCF per Share",
                "EPS",
                "YoY Revenue Growth",
                "YoY EPS Growth",
                "YoY FCF Growth",
            ],
            "Current Quarter": [
                revenue,
                gross_profit,
                net_income,
                gross_margin,
                net_income_margin,
                free_cash_flow,
                fcf_per_share,
                eps,
                yoy_revenue_growth,
                yoy_eps_growth,
                yoy_fcf_growth,
            ],
            "TTM": [
                ttm_revenue,
                ttm_gross_profit,
                ttm_net_income,
                ttm_gross_profit / ttm_revenue if ttm_revenue else None,
                ttm_net_income / ttm_revenue if ttm_revenue else None,
                ttm_free_cash_flow,
                ttm_fcf_per_share,
                ttm_eps,
                None,
                None,
                None,
            ],
        }

        metrics_df = pd.DataFrame(metrics_data)
        return metrics_df
    return None

def get_earnings_date(ticker):
    """
    Fetch the next earnings date for the given ticker.
    Use the /historical/earning_calendar/{ticker} endpoint.
    """
    url = f"https://financialmodelingprep.com/api/v3/historical/earning_calendar/{ticker}?apikey={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data:
            # Convert the dates to datetime and filter for future dates
            today = datetime.today()
            earnings_dates = pd.DataFrame(data)
            earnings_dates["date"] = pd.to_datetime(earnings_dates["date"])
            future_dates = earnings_dates[earnings_dates["date"] > today]
            
            # Find the closest date in the future
            if not future_dates.empty:
                next_earnings_date = future_dates.sort_values("date").iloc[0]["date"]
                return next_earnings_date
    return None
def get_analyst_estimates(ticker):
    """Fetch quarterly analyst estimates for the given ticker."""
    url = f"https://financialmodelingprep.com/api/v3/analyst-estimates/{ticker}?period=quarter&apikey={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data:
            return pd.DataFrame(data)
    return None
# Stock Deep Dive Page
st.title("Stock Deep Dive")

# Input field for ticker
ticker = st.text_input("Enter the stock ticker (e.g., AAPL):")

if ticker:
    # Fetch historical prices and profile information
    stock_prices = get_historical_prices(ticker)
    stock_profile = get_profile(ticker)
    day_return, qtd_return = calculate_returns(stock_prices)

    # Sidebar with profile information and returns data
    with st.sidebar:
        if stock_profile:
            st.subheader(f"{ticker.upper()} Profile")
            st.write(f"**Company Name:** {stock_profile.get('companyName', 'N/A')}")
            st.write(f"**Sector:** {stock_profile.get('sector', 'N/A')}")
            st.write(f"**Industry:** {stock_profile.get('industry', 'N/A')}")
            st.write(f"**Exchange:** {stock_profile.get('exchange', 'N/A')}")
            st.write(f"**Website:** [{stock_profile.get('website', 'N/A')}]({stock_profile.get('website', '')})")
            st.write(f"**Description:** {stock_profile.get('description', 'N/A')}")

        st.subheader(f"{ticker.upper()} Returns")
        st.metric("Day Return", f"{day_return:.2f}%" if day_return is not None else "N/A")
        st.metric("QTD Return", f"{qtd_return:.2f}%" if qtd_return is not None else "N/A")

    if stock_prices is not None:
        # Add chart buttons
        st.subheader("Historical Price Chart")
        chart_view = st.radio("Select Time Period:", ["QTD", "YTD", "1Y"], index=0)

        # Filter data based on selection
        today = datetime.today()
        if chart_view == "QTD":
            start_date = datetime(today.year, (today.month - 1) // 3 * 3 + 1, 1)- timedelta(days=1)
        elif chart_view == "YTD":
            start_date = datetime(today.year, 1, 1)- timedelta(days=1)
        elif chart_view == "1Y":
            start_date = today - timedelta(days=365) - timedelta(days=1)

        
 
        filtered_prices = stock_prices[stock_prices["date"] >= start_date]

        # Add SPY toggle
        add_spy = st.checkbox("Add SPY to the Chart", value=False)
        spy_prices = get_historical_prices("SPY") if add_spy else None
        filtered_spy_prices = (
            spy_prices[spy_prices["date"] >= start_date] if spy_prices is not None else None
        )

        # Rebase toggle
        rebase = st.checkbox("Rebase Prices (Show Cumulative Returns)", value=False)

        # Create Plotly chart
        fig = go.Figure()

        # Plot stock prices or cumulative returns
        if rebase:
            rebased_stock_returns = rebase_prices(filtered_prices["close"]) if not filtered_prices.empty else None
            if rebased_stock_returns is not None:
                fig.add_trace(
                    go.Scatter(
                        x=filtered_prices["date"],
                        y=rebased_stock_returns,
                        mode="lines",
                        name=f"{ticker.upper()} (Cumulative Return)",
                        line=dict(color="blue"),
                    )
                )
            if add_spy and filtered_spy_prices is not None:
                rebased_spy_returns = rebase_prices(filtered_spy_prices["close"])
                fig.add_trace(
                    go.Scatter(
                        x=filtered_spy_prices["date"],
                        y=rebased_spy_returns,
                        mode="lines",
                        name="SPY (Cumulative Return)",
                        line=dict(color="red"),
                    )
                )
            fig.update_layout(yaxis_title="Cumulative Return (%)")
        else:
            # Plot actual prices
            fig.add_trace(
                go.Scatter(
                    x=filtered_prices["date"],
                    y=filtered_prices["close"],
                    mode="lines",
                    name=f"{ticker.upper()} Price",
                    line=dict(color="blue"),
                )
            )
            if add_spy and filtered_spy_prices is not None:
                fig.add_trace(
                    go.Scatter(
                        x=filtered_spy_prices["date"],
                        y=filtered_spy_prices["close"],
                        mode="lines",
                        name="SPY Price",
                        line=dict(color="red"),
                    )
                )
            fig.update_layout(yaxis_title="Price (USD)")

        # Customize chart layout
        fig.update_layout(
            title=f"{ticker.upper()} vs. SPY ({chart_view})",
            xaxis_title="Date",
            legend_title="Assets",
            template="plotly_white",
        )

        # Display chart
        st.plotly_chart(fig, use_container_width=True)
        st.subheader(f"{ticker.upper()} Financial Metrics")
        metrics_df = calculate_financial_metrics(ticker)
        if metrics_df is not None:
            # Ensure all numeric columns are properly formatted
            for col in ["Current Quarter", "TTM"]:
                metrics_df[col] = pd.to_numeric(metrics_df[col], errors="coerce")

            # Display the table with formatted numbers and "N/A" for missing values
            st.dataframe(
                metrics_df.style.format(
                    {
                        "Current Quarter": "{:.2f}",
                        "TTM": "{:.2f}",
                    },
                    na_rep="N/A",
                )
            )
        else:
            st.error(f"Could not fetch financial metrics for {ticker.upper()}.")

# Fetch and display the next earnings date
        next_earnings_date = get_earnings_date(ticker)
       
        if next_earnings_date:
            st.subheader(f"Next Earnings Date for {ticker.upper()}")
            st.write(f"**Next Earnings Date:** {next_earnings_date}")
        else:
            st.warning(f"Next earnings date for {ticker.upper()} is not available.")

        # Fetch and display analyst estimates
        analyst_estimates = get_analyst_estimates(ticker)
        if analyst_estimates is not None:
            # Filter dates starting 2 months before today
            two_months_ago = datetime.today() - timedelta(days=60)
            analyst_estimates["date"] = pd.to_datetime(analyst_estimates["date"])
            filtered_estimates = analyst_estimates[
                analyst_estimates["date"] >= two_months_ago
            ].head(5)

            if not filtered_estimates.empty:
                st.subheader(f"{ticker.upper()} Analyst Estimates")
                # Display the first 5 columns starting from the filtered date
                st.dataframe(filtered_estimates)
            else:
                st.warning(f"No analyst estimates available for {ticker.upper()} in the selected date range.")
        else:
            st.error(f"Could not fetch analyst estimates for {ticker.upper()}.")
    else:
        st.error(f"Could not fetch data for {ticker.upper()}. Please try another ticker.")