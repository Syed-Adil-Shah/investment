
# Streamlit application integrating commission entry and enhanced Sector P/L (%) chart

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Configuration ---
SHEET_ID = "1ynUU8iGF3FqM1gxQUVaGfLCR3WvTv1uXtZpME6q6HXE"
SHEET_NAME = "Sheet1"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_FILE = "gspread_credentials.json"  # Replace with your actual credentials file path

# --- Google Sheets Setup ---
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPES)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
df = pd.DataFrame(sheet.get_all_records())

# --- UI for Trade Entry ---
st.title("📊 Stock Portfolio Tracker")

col1, col2 = st.columns([3, 2])
with col1:
    ticker = st.text_input("Stock Ticker")
    buy_price = st.number_input("Buy Price ($)", value=0.0, step=0.01)
    shares = st.number_input("Shares", value=0.0, step=0.01)
    commission = st.number_input("Commission ($)", value=0.0, step=0.01)
with col2:
    buy_date = st.date_input("Buy Date")
    sector = st.selectbox("Sector", options=sorted(df["Sector"].unique().tolist() + ["Other"]))

if st.button("💾 Add Trade"):
    sheet.append_row([ticker, str(buy_date), buy_price, "", shares, sector, "", commission])
    st.success("Trade added successfully!")

# --- Portfolio Summary ---
df["Total Invested"] = df["Buy Price"] * df["Shares"] + df.get("Commission", 0)
df["Market Value"] = df["Sell Price"].fillna(0) * df["Shares"]
df["P/L ($)"] = df["Market Value"] - df["Total Invested"]
df["P/L (%)"] = (df["P/L ($)"] / df["Total Invested"]) * 100

total_invested = df["Total Invested"].sum()
market_value = df["Market Value"].sum()
total_pl = df["P/L ($)"].sum()

st.subheader("💼 Portfolio Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Total Invested", f"${total_invested:.2f}")
col2.metric("Market Value", f"${market_value:.2f}")
col3.metric("Total P/L", f"${total_pl:.2f}", f"{(total_pl / total_invested) * 100:.2f}%")

# --- Sector P/L Visualization ---
sector_df = df.groupby("Sector").agg({
    "Total Invested": "sum",
    "P/L ($)": "sum"
}).reset_index()
sector_df["P/L (%)"] = (sector_df["P/L ($)"] / sector_df["Total Invested"]) * 100
sector_df = sector_df.sort_values(by="P/L (%)", ascending=False)

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(sector_df["Sector"], sector_df["P/L (%)"], color="teal")
ax.set_ylabel("P/L (%)")
ax.set_title("Sector Profit/Loss (%)")
ax.tick_params(axis="x", labelrotation=30)
for bar, pct in zip(bars, sector_df["P/L (%)"]):
    height = bar.get_height()
    ax.annotate(f"{pct:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 5 if pct >= 0 else -15), textcoords="offset points",
                ha='center', va='bottom' if pct >= 0 else 'top',
                fontsize=10, weight='bold')

st.subheader("📈 Sector P/L")
st.pyplot(fig)
