import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client
import os

# --- Supabase Connection ---
rl = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- Helper Functions ---
def get_user_portfolio(user_email):
    response = supabase.table("portfolios").select("*").eq("user_email", user_email).execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame(columns=["ticker", "transaction_type", "price", "shares", "date", "sector"])

def insert_transaction(data):
    supabase.table("portfolios").insert(data).execute()

def calculate_portfolio(df):
    buy_df = df[df["transaction_type"] == "BUY"]
    sell_df = df[df["transaction_type"] == "SELL"]

    summary = []
    tickers = buy_df["ticker"].unique()
    for ticker in tickers:
        buys = buy_df[buy_df["ticker"] == ticker]
        sells = sell_df[sell_df["ticker"] == ticker]

        total_bought = buys["shares"].sum()
        total_sold = sells["shares"].sum()
        avg_price = (buys["shares"] * buys["price"]).sum() / total_bought if total_bought > 0 else 0
        net_shares = total_bought - total_sold

        proceeds = (sells["shares"] * sells["price"]).sum()
        cost_basis_sold = avg_price * total_sold
        realized_gain = proceeds - cost_basis_sold
        unrealized_gain = 0
        current_price = 0

        # Get latest price
        try:
            import yfinance as yf
            data = yf.Ticker(ticker).history(period="1d")
            current_price = data["Close"].iloc[-1]
            unrealized_gain = (current_price - avg_price) * net_shares
        except:
            pass

        summary.append({
            "Ticker": ticker,
            "Shares Held": net_shares,
            "Avg Buy Price": round(avg_price, 2),
            "Current Price": round(current_price, 2),
            "Unrealized Gain ($)": round(unrealized_gain, 2),
            "Realized Gain ($)": round(realized_gain, 2)
        })

    return pd.DataFrame(summary)

# --- App UI ---
st.title("📊 Multi-User Stock Portfolio Tracker")

user_email = st.text_input("Enter your email to login:", value="", placeholder="your@email.com")

if user_email:
    st.markdown("### ➕ Add Transaction")
    with st.form("add_trade"):
        col1, col2 = st.columns(2)
        ticker = col1.text_input("Ticker").upper().strip()
        txn_type = col2.selectbox("Transaction Type", ["BUY", "SELL"])
        col3, col4 = st.columns(2)
        price = col3.number_input("Price", min_value=0.0)
        shares = col4.number_input("Shares", min_value=0.0, format="%.4f")
        date = st.date_input("Date", datetime.date.today())
        sector = st.text_input("Sector (only for BUY)", value="") if txn_type == "BUY" else ""
        submit = st.form_submit_button("Save Transaction")

        if submit and ticker and shares > 0 and price > 0:
            insert_transaction({
                "user_email": user_email,
                "ticker": ticker,
                "transaction_type": txn_type,
                "price": price,
                "shares": shares,
                "date": str(date),
                "sector": sector
            })
            st.success(f"{txn_type} transaction added for {ticker}.")

    # --- Load Portfolio ---
    df = get_user_portfolio(user_email)
    if not df.empty:
        summary = calculate_portfolio(df)
        st.subheader("📈 Portfolio Summary")
        st.dataframe(summary)

        total_unrealized = summary["Unrealized Gain ($)"].sum()
        total_realized = summary["Realized Gain ($)"].sum()
        col1, col2 = st.columns(2)
        col1.metric("Unrealized Gain", f"${total_unrealized:,.2f}")
        col2.metric("Realized Gain", f"${total_realized:,.2f}")
    else:
        st.info("No transactions found.")
