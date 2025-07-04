import streamlit as st
import pandas as pd
import datetime
import yfinance as yf
from supabase import create_client, Client

# --- Supabase Setup ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- Functions ---
def get_user_portfolio(user_email):
    res = supabase.table("portfolios").select("*").eq("user_email", user_email).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=["ticker", "transaction_type", "price", "shares", "date", "sector"])

def insert_transaction(data):
    supabase.table("portfolios").insert(data).execute()

def calculate_portfolio(df):
    buy_df = df[df["transaction_type"] == "BUY"]
    sell_df = df[df["transaction_type"] == "SELL"]

    summary = []
    for ticker in buy_df["ticker"].unique():
        buys = buy_df[buy_df["ticker"] == ticker]
        sells = sell_df[sell_df["ticker"] == ticker]

        total_bought = buys["shares"].sum()
        total_sold = sells["shares"].sum()
        avg_price = (buys["shares"] * buys["price"]).sum() / total_bought if total_bought else 0
        net_shares = total_bought - total_sold
        proceeds = (sells["shares"] * sells["price"]).sum()
        realized = proceeds - (avg_price * total_sold)

        current_price, unrealized = 0, 0
        try:
            hist = yf.Ticker(ticker).history(period="1d")
            current_price = hist["Close"].iloc[-1]
            unrealized = (current_price - avg_price) * net_shares
        except:
            pass

        summary.append({
            "Ticker": ticker,
            "Shares Held": net_shares,
            "Avg Buy Price": round(avg_price, 2),
            "Current Price": round(current_price, 2),
            "Unrealized Gain ($)": round(unrealized, 2),
            "Realized Gain ($)": round(realized, 2)
        })

    return pd.DataFrame(summary)

# --- UI ---
st.title("📊 Stock Portfolio Tracker (Multi-User with Supabase)")

user_email = st.text_input("Enter your email to continue:")

if user_email:
    st.markdown("### ➕ Add Transaction")
    with st.form("entry_form"):
        col1, col2 = st.columns(2)
        ticker = col1.text_input("Ticker").upper().strip()
        txn_type = col2.selectbox("Type", ["BUY", "SELL"])
        col3, col4 = st.columns(2)
        price = col3.number_input("Price", min_value=0.0)
        shares = col4.number_input("Shares", min_value=0.0, format="%.4f")
        date = st.date_input("Date", datetime.date.today())
        sector = st.text_input("Sector (for BUY only):") if txn_type == "BUY" else ""
        submitted = st.form_submit_button("Submit")

        if submitted and ticker and shares > 0 and price > 0:
            insert_transaction({
                "user_email": user_email,
                "ticker": ticker,
                "transaction_type": txn_type,
                "price": price,
                "shares": shares,
                "date": str(date),
                "sector": sector
            })
            st.success(f"{txn_type} for {shares} {ticker} at ${price} saved!")

    df = get_user_portfolio(user_email)
    if not df.empty:
        st.markdown("### 📈 Portfolio Overview")
        summary = calculate_portfolio(df)
        st.dataframe(summary)

        total_realized = summary["Realized Gain ($)"].sum()
        total_unrealized = summary["Unrealized Gain ($)"].sum()

        col1, col2 = st.columns(2)
        col1.metric("Realized Gain", f"${total_realized:,.2f}")
        col2.metric("Unrealized Gain", f"${total_unrealized:,.2f}")
    else:
        st.info("No transactions found for this email.")