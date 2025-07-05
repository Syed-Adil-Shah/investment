
import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2 import service_account
from datetime import datetime

# === GOOGLE SHEETS SETUP ===
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = "1NYUM9a82Ecj3g80k8FojDeuZ1PB7DRuQ19Gp1JhkkBk"  # Replace with your actual Sheet ID
SHEET_NAME = "Sheet1"

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES
)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
data = sheet.get_all_records()
df = pd.DataFrame(data)

# === APP UI ===
st.title("📊 Stock Portfolio Tracker")

with st.form("trade_form"):
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker = st.text_input("Stock Ticker")
    with col2:
        buy_date = st.date_input("Buy Date", value=datetime.today())

    col3, col4 = st.columns([2, 2])
    with col3:
        buy_price = st.number_input("Buy Price ($)", min_value=0.0, format="%.2f")
    with col4:
        shares = st.number_input("Shares", min_value=0.0, format="%.6f")

    sector = st.selectbox("Sector", ["Technology", "Energy", "Healthcare", "Consumer Goods", "Financials", "Materials"])

    submitted = st.form_submit_button("💾 Add Trade")

    if submitted and ticker and buy_price > 0 and shares > 0:
        new_row = [ticker, str(buy_date), "Buy", buy_price, "", shares, sector, ""]
        sheet.append_row(new_row)
        st.success("Trade added!")

if not df.empty:
    st.subheader("📌 Sector-wise P/L (%)")

    df["Buy Price"] = pd.to_numeric(df["Buy Price"], errors="coerce")
    df["Sell Price"] = pd.to_numeric(df["Sell Price"], errors="coerce")
    df["Shares"] = pd.to_numeric(df["Shares"], errors="coerce")
    df["Current Value"] = df["Buy Price"] * df["Shares"]

    df["Current PL $"] = (df["Sell Price"] - df["Buy Price"]) * df["Shares"]

    sector_pl = df.groupby("Sector").agg({
        "Buy Price": lambda x: (x * df.loc[x.index, "Shares"]).sum(),
        "Current PL $": "sum"
    }).rename(columns={"Buy Price": "Total Invested", "Current PL $": "Unrealized P/L"})

    sector_pl["PL %"] = (sector_pl["Unrealized P/L"] / sector_pl["Total Invested"]) * 100
    sector_pl.reset_index(inplace=True)

    fig = px.bar(sector_pl, x="Sector", y="PL %", text="PL %", title="Sector-wise Profit/Loss (%)")
    fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    fig.update_layout(yaxis_title="P/L (%)", xaxis_title="Sector", uniformtext_minsize=8, uniformtext_mode="hide")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Add trades to get started.")
