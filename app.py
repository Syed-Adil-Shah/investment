import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import matplotlib.pyplot as plt

st.set_page_config(page_title="Stock Portfolio Tracker", layout="wide")

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["gcp_service_account"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(credentials)

sheet = client.open("StockPortfolioData").worksheet("Portfolio")
data = pd.DataFrame(sheet.get_all_records())

# Sidebar - Add New Trade
st.sidebar.header("📥 Add Trade")
with st.sidebar.form("trade_form"):
    ticker = st.text_input("Ticker").upper()
    date = st.date_input("Date", value=datetime.today())
    action = st.selectbox("Action", ["Buy", "Sell"])
    price = st.number_input("Price", min_value=0.0, format="%.2f")
    shares = st.number_input("Shares", min_value=1, step=1)
    sector = st.selectbox("Sector", ["Technology", "Healthcare", "Financials", "Energy", "Consumer Goods", "Materials", "Other"])
    submitted = st.form_submit_button("Add Trade")

    if submitted and ticker and price > 0:
        new_row = [ticker, str(date), action, price if action == "Buy" else "", shares, price if action == "Sell" else "", sector]
        sheet.append_row(new_row)
        st.success("Trade added successfully!")
        st.experimental_rerun()

# Process Data
data["Buy Price"] = pd.to_numeric(data["Buy Price"], errors="coerce")
data["Sell Price"] = pd.to_numeric(data["Sell Price"], errors="coerce")
data["Shares"] = pd.to_numeric(data["Shares"], errors="coerce")
data["Remaining Shares"] = 0

portfolio = []

for ticker in data["Ticker"].unique():
    df_ticker = data[data["Ticker"] == ticker].copy()
    buys = df_ticker[df_ticker["Action"] == "Buy"]
    sells = df_ticker[df_ticker["Action"] == "Sell"]
    total_bought = buys["Shares"].sum()
    total_sold = sells["Shares"].sum()
    remaining = total_bought - total_sold
    avg_buy = (buys["Buy Price"] * buys["Shares"]).sum() / total_bought if total_bought > 0 else 0
    sector = buys["Sector"].iloc[0] if not buys.empty else "Other"

    current_price = 33.51 if ticker == "SLV" else avg_buy * 1.1  # Stub price
    invested = avg_buy * total_bought
    market_value = current_price * remaining
    realized_pl = (sells["Sell Price"] * sells["Shares"]).sum() - avg_buy * total_sold
    unrealized_pl = market_value - avg_buy * remaining
    total_pl = realized_pl + unrealized_pl

    portfolio.append({
        "Ticker": ticker,
        "Total Shares": total_bought,
        "Sold Shares": total_sold,
        "Remaining Shares": remaining,
        "Avg Buy Price": f"${avg_buy:.2f}",
        "Current Price": f"${current_price:.2f}",
        "Invested": f"${avg_buy * total_bought:.2f}",
        "Market Value": f"${market_value:.2f}",
        "Realized P/L": f"${realized_pl:.2f}",
        "Unrealized P/L": f"${unrealized_pl:.2f}",
        "Total P/L": f"${total_pl:.2f}",
        "Sector": sector
    })

df_portfolio = pd.DataFrame(portfolio)
if not df_portfolio.empty:
    total_invested = df_portfolio["Invested"].str.replace("$", "").astype(float).sum()
    market_value = df_portfolio["Market Value"].str.replace("$", "").astype(float).sum()
    total_pl = df_portfolio["Total P/L"].str.replace("$", "").astype(float).sum()
    unrealized = df_portfolio["Unrealized P/L"].str.replace("$", "").astype(float).sum()
    realized = df_portfolio["Realized P/L"].str.replace("$", "").astype(float).sum()
    pct_pl = (total_pl / total_invested) * 100 if total_invested > 0 else 0
else:
    total_invested = market_value = total_pl = unrealized = realized = pct_pl = 0

# UI Layout
st.title("📊 Stock Portfolio Tracker")
col1, col2, col3 = st.columns(3)
col1.metric("Total Invested", f"${total_invested:.2f}")
col2.metric("Market Value", f"${market_value:.2f}")
col3.metric("Total P/L", f"${total_pl:.2f}", f"{pct_pl:.2f}%")

st.markdown(f"**Realized P/L:** ${realized:.2f}")
st.markdown(f"**Unrealized P/L:** ${unrealized:.2f}")

# Sector Pie Chart
if not df_portfolio.empty:
    st.subheader("🧩 Sector Allocation")
    fig1, ax1 = plt.subplots()
    sector_data = df_portfolio.groupby("Sector")["Market Value"].apply(lambda x: x.str.replace("$", "").astype(float).sum())
    ax1.pie(sector_data, labels=sector_data.index, autopct="%1.1f%%")
    ax1.axis("equal")
    st.pyplot(fig1)

# Portfolio Table
st.subheader("📝 Portfolio Table")
st.dataframe(df_portfolio)