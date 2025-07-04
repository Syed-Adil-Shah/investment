import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("📊 Simple Portfolio Tracker")

# Load session data or initialize
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["Ticker", "Date", "Action", "Price", "Shares", "Sector"])

# Add Trade
with st.form("Add Trade"):
    ticker = st.text_input("Ticker").upper()
    date = st.date_input("Date")
    action = st.selectbox("Action", ["Buy", "Sell"])
    price = st.number_input("Price", min_value=0.0)
    shares = st.number_input("Shares", min_value=0.0, step=0.1)
    sector = st.text_input("Sector")
    submitted = st.form_submit_button("Submit")
    if submitted:
        new_trade = pd.DataFrame([[ticker, date, action, price, shares, sector]], columns=st.session_state.portfolio.columns)
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_trade], ignore_index=True)
        st.success("Trade added!")

# Display portfolio
st.subheader("Trade History")
st.dataframe(st.session_state.portfolio)

# Bar chart of sector allocation (percent based on invested amount)
if not st.session_state.portfolio.empty:
    buy_df = st.session_state.portfolio[st.session_state.portfolio["Action"] == "Buy"]
    buy_df["Invested"] = buy_df["Price"] * buy_df["Shares"]
    sector_group = buy_df.groupby("Sector")["Invested"].sum()
    sector_percent = (sector_group / sector_group.sum()) * 100

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(sector_percent.index, sector_percent.values)
    ax.set_ylabel("Allocation (%)")
    ax.set_title("Sector Allocation")
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 1, f"{yval:.1f}%", ha='center')
    st.pyplot(fig)