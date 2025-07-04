import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client, Client

# Connect to Supabase using Streamlit secrets
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("📊 Personal Portfolio Tracker")

# Load existing data from Supabase
@st.cache_data(ttl=300)
def load_data():
    response = supabase.table("portfolio").select("*").execute()
    df = pd.DataFrame(response.data)
    return df

df = load_data()

# Form to add new trade
with st.form("add_trade"):
    st.subheader("Add Trade")
    ticker = st.text_input("Ticker")
    date = st.date_input("Trade Date")
    price = st.number_input("Price", min_value=0.0)
    shares = st.number_input("Shares", min_value=0.01, step=0.01)
    sector = st.selectbox("Sector", ["Technology", "Healthcare", "Financials", "Energy", "Consumer Goods", "Materials", "Other"])
    trade_type = st.selectbox("Type", ["Buy", "Sell"])
    submitted = st.form_submit_button("Submit")
    if submitted and ticker:
        new_data = {
            "ticker": ticker.upper(),
            "date": str(date),
            "price": price,
            "shares": shares,
            "sector": sector,
            "type": trade_type
        }
        supabase.table("portfolio").insert(new_data).execute()
        st.success(f"Trade for {ticker.upper()} added.")
        st.experimental_rerun()

# Display current data
st.subheader("Current Portfolio Data")
st.dataframe(df)

# Show sector breakdown
st.subheader("Sector Summary")
if not df.empty:
    summary = df.groupby("sector")["shares"].sum().reset_index()
    st.bar_chart(summary.set_index("sector"))