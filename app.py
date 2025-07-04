import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt

# Authenticate with Google Sheets using Streamlit secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gspread"], scope)
client = gspread.authorize(creds)

# Google Sheet setup
SHEET_NAME = "StockPortfolioData"
worksheet = client.open(SHEET_NAME).worksheet("Portfolio")

# Load data from Google Sheet
data = worksheet.get_all_records()
df = pd.DataFrame(data)
if not df.empty:
    df["Date"] = pd.to_datetime(df["Date"])

st.set_page_config(page_title="Stock Portfolio Tracker", layout="wide")
st.title("📊 Stock Portfolio Tracker")

# Portfolio calculations
df["Ticker"] = df["Ticker"].str.upper()
buys = df[df["Action"] == "Buy"].copy()
sells = df[df["Action"] == "Sell"].copy()

portfolio = []
for ticker in df["Ticker"].unique():
    b = buys[buys["Ticker"] == ticker]
    s = sells[sells["Ticker"] == ticker]

    total_bought = b["Shares"].sum()
    total_sold = s["Shares"].sum()
    remaining = total_bought - total_sold
    invested = (b["Shares"] * b["Buy Price"]).sum()
    sold_value = (s["Shares"] * s["Sell Price"]).sum()
    avg_buy = invested / total_bought if total_bought > 0 else 0

    try:
        current_price = yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
    except:
        current_price = 0

    market_value = current_price * remaining
    unrealized_pl = (current_price - avg_buy) * remaining
    realized_pl = sold_value - (avg_buy * total_sold)
    total_pl = unrealized_pl + realized_pl

    sector = b["Sector"].iloc[0] if not b.empty else s["Sector"].iloc[0] if not s.empty else "Other"
    portfolio.append({
        "Ticker": ticker,
        "Total Shares": total_bought,
        "Sold Shares": total_sold,
        "Remaining Shares": remaining,
        "Avg Buy Price": avg_buy,
        "Current Price": current_price,
        "Invested": invested,
        "Market Value": market_value,
        "Realized P/L": realized_pl,
        "Unrealized P/L": unrealized_pl,
        "Total P/L": total_pl,
        "Sector": sector
    })

# Display
agg = pd.DataFrame(portfolio)
total_invested = agg["Invested"].sum()
total_mv = agg["Market Value"].sum()
total_realized = agg["Realized P/L"].sum()
total_unrealized = agg["Unrealized P/L"].sum()
total_pl = agg["Total P/L"].sum()
total_pl_pct = (total_pl / total_invested) * 100 if total_invested else 0
agg["Portfolio %"] = (agg["Invested"] / total_invested) * 100 if total_invested else 0

# UI Layout
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown("### 💼 Portfolio Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Invested", f"${total_invested:,.2f}")
    c2.metric("Market Value", f"${total_mv:,.2f}")
    c3.metric("Total P/L", f"${total_pl:,.2f}", f"{total_pl_pct:.2f}%")
    st.write(f"**Realized P/L:** ${total_realized:,.2f}")
    st.write(f"**Unrealized P/L:** ${total_unrealized:,.2f}")

with col2:
    st.markdown("### 🧩 Sector Allocation")
    pie_data = agg.groupby("Sector")["Invested"].sum()
    fig1, ax1 = plt.subplots(figsize=(3, 3))
    ax1.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%", startangle=90)
    ax1.axis("equal")
    st.pyplot(fig1)

with col3:
    st.markdown("### 📈 Sector Unrealized P/L")
    sector_pl = agg.groupby("Sector")["Unrealized P/L"].sum()
    fig2, ax2 = plt.subplots(figsize=(3, 2))
    sector_pl.plot(kind="bar", ax=ax2, color="teal")
    ax2.set_ylabel("Unrealized P/L ($)")
    ax2.set_title("Sector Unrealized P/L")
    st.pyplot(fig2)

# Table
st.subheader("🧾 Portfolio Table")
st.dataframe(agg.style.format({
    "Avg Buy Price": "${:.2f}",
    "Current Price": "${:.2f}",
    "Market Value": "${:.2f}",
    "Invested": "${:.2f}",
    "Realized P/L": "${:.2f}",
    "Unrealized P/L": "${:.2f}",
    "Total P/L": "${:.2f}",
    "Portfolio %": "{:.2f}%"
}), use_container_width=True)