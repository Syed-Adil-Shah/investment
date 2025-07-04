
import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import plotly.express as px

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = {
  "type": "service_account",
  "project_id": "investment-tracker-464915",
  "private_key_id": "25f6098232b8",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQD...<TRUNCATED FOR SECURITY>...\n-----END PRIVATE KEY-----\n",
  "client_email": "streamlit-sheets-access@investment-tracker-464915.iam.gserviceaccount.com",
  "client_id": "114755555246802256347",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/streamlit-sheets-access%40investment-tracker-464915.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(credentials)
sheet = client.open("StockPortfolioData").sheet1

# Load data
data = pd.DataFrame(sheet.get_all_records())

st.set_page_config(page_title="Stock Portfolio Tracker", layout="wide")
st.title("📊 Stock Portfolio Tracker")

# Sidebar form
with st.sidebar.form("trade_form"):
    st.subheader("💹 Add Trade")
    ticker = st.text_input("Ticker").upper()
    date = st.date_input("Date", datetime.today())
    action = st.selectbox("Action", ["Buy", "Sell"])
    price = st.number_input("Price", min_value=0.0, step=0.01)
    shares = st.number_input("Shares", min_value=1, step=1)
    sector = st.selectbox("Sector", ["Technology", "Healthcare", "Financials", "Energy", "Consumer", "Utilities", "Other"])
    submit = st.form_submit_button("Add Trade")

    if submit and ticker:
        sheet.append_row([
            ticker, str(date), action, price if action == "Buy" else "",
            shares, price if action == "Sell" else "", sector
        ])
        st.success("Trade added! Please refresh.")

# Process data
if not data.empty:
    buys = data[data["Action"] == "Buy"].copy()
    sells = data[data["Action"] == "Sell"].copy()
    merged = buys.groupby("Ticker").agg({
        "Buy Price": "mean",
        "Shares": "sum",
        "Sector": "first"
    }).rename(columns={"Buy Price": "Avg Buy Price", "Shares": "Total Shares"}).reset_index()

    sell_agg = sells.groupby("Ticker")["Shares"].sum().reset_index().rename(columns={"Shares": "Sold Shares"})
    merged = pd.merge(merged, sell_agg, on="Ticker", how="left").fillna(0)
    merged["Remaining Shares"] = merged["Total Shares"] - merged["Sold Shares"]
    merged = merged[merged["Remaining Shares"] > 0]

    # Live price & calculations
    def get_price(ticker):
        try:
            return yf.Ticker(ticker).info["regularMarketPrice"]
        except:
            return 0

    merged["Current Price"] = merged["Ticker"].apply(get_price)
    merged["Invested"] = merged["Avg Buy Price"] * merged["Remaining Shares"]
    merged["Market Value"] = merged["Current Price"] * merged["Remaining Shares"]
    merged["Realized P/L"] = sells.groupby("Ticker").apply(
        lambda g: (g["Sell Price"] * g["Shares"]).sum() - buys.loc[buys["Ticker"] == g.name, "Buy Price"].mean() * g["Shares"].sum()
    ).reset_index(drop=True).fillna(0)
    merged["Unrealized P/L"] = merged["Market Value"] - merged["Invested"]
    merged["Total P/L"] = merged["Realized P/L"] + merged["Unrealized P/L"]
    total_invested = merged["Invested"].sum()
    merged["Portfolio %"] = merged["Market Value"] / merged["Market Value"].sum()

    # Summary
    st.header("📂 Portfolio Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Invested", f"${total_invested:,.2f}")
    col2.metric("Market Value", f"${merged['Market Value'].sum():,.2f}")
    col3.metric("Total P/L", f"${merged['Total P/L'].sum():,.2f}", f"{(merged['Total P/L'].sum() / total_invested) * 100:.2f}%")

    # Realized & Unrealized
    st.markdown(f"**Realized P/L:** ${merged['Realized P/L'].sum():.2f}")
    st.markdown(f"**Unrealized P/L:** ${merged['Unrealized P/L'].sum():.2f}")

    # Charts
    st.header("🧩 Sector Allocation")
    fig1 = px.pie(merged, values="Portfolio %", names="Sector", title="Sector Allocation")
    st.plotly_chart(fig1, use_container_width=True)

    st.header("📈 Sector Unrealized P/L")
    fig2 = px.bar(merged.groupby("Sector")["Unrealized P/L"].sum().reset_index(), x="Sector", y="Unrealized P/L")
    st.plotly_chart(fig2, use_container_width=True)

    # Table
    st.header("🗒 Portfolio Table")
    st.dataframe(merged.style.format({
        "Avg Buy Price": "${:.2f}",
        "Current Price": "${:.2f}",
        "Invested": "${:.2f}",
        "Market Value": "${:.2f}",
        "Realized P/L": "${:.2f}",
        "Unrealized P/L": "${:.2f}",
        "Total P/L": "${:.2f}",
        "Portfolio %": "{:.2%}"
    }), use_container_width=True)
else:
    st.warning("No data yet. Add your first trade.")
