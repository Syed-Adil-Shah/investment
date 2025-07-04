import streamlit as st
import pandas as pd
import yfinance as yf
from postgrest import PostgrestClient
import httpx

# Supabase config (use your secrets)
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Connect to Supabase using Postgrest
client = httpx.Client(headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1", client=client)

# Title
st.title("📊 Stock Journal Tracker (with Supabase)")

# Trade Entry
st.subheader("Add Trade")
with st.form("trade_form"):
    instrument = st.selectbox("Instrument Type", ["Stock", "Crypto", "Forex"])
    trade_name = st.text_input("Trade Name")
    entry_price = st.number_input("Entry Price", min_value=0.0)
    sell_price = st.number_input("Sell Price (0 if not sold)", min_value=0.0)
    long_short = st.selectbox("Position Type", ["Long", "Short"])
    strategy = st.text_input("Strategy Name")
    confluence = st.text_area("Confluence / Notes")
    action = st.selectbox("Buy or Sell", ["Buy", "Sell"])
    submitted = st.form_submit_button("Add Trade")

    if submitted:
        result = postgrest.table("trades").insert({
            "instrument": instrument,
            "trade_name": trade_name,
            "entry_price": entry_price,
            "sell_price": sell_price,
            "long_short": long_short,
            "strategy": strategy,
            "confluence": confluence,
            "action": action
        }).execute()
        st.success("Trade added!")

# Display Table
st.subheader("📋 Trade History")
res = postgrest.table("trades").select("*").execute()
df = pd.DataFrame(res.data)

if not df.empty:
    df["realized_gain"] = (df["sell_price"] - df["entry_price"]).round(2)
    df["unrealized_gain"] = df.apply(
        lambda row: yf.Ticker(row["trade_name"]).history(period="1d")["Close"].iloc[-1] - row["entry_price"]
        if row["sell_price"] == 0 else 0,
        axis=1
    ).round(2)
    st.dataframe(df)

# Bar chart of gains
if not df.empty:
    st.subheader("📈 Gains Overview")
    gain_chart = df[["trade_name", "realized_gain", "unrealized_gain"]].set_index("trade_name")
    st.bar_chart(gain_chart)
