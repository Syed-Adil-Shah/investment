
import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import matplotlib.pyplot as plt
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

# === CONFIG ===
st.set_page_config(page_title="Stock Portfolio Tracker", layout="wide", page_icon="📈")
SHEET_ID = "12Aje52kDt7nh0uk4aLpPyaYiVMivQrornyuwUP3bJew"
SHEET_NAME = "Sheet1"

# === AUTHENTICATION ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# === LOAD DATA ===
try:
    df = get_as_dataframe(sheet, evaluate_formulas=True).dropna(how='all')
    df['Date'] = pd.to_datetime(df['Date'])
except Exception as e:
    df = pd.DataFrame(columns=['Ticker', 'Date', 'Buy Price', 'Shares', 'Sector'])

st.title("📊 Stock Portfolio Tracker")

# === TRADE ENTRY ===
with st.form("Add Entry"):
    col1, col2 = st.columns(2)
    ticker = col1.text_input("Stock Ticker").strip().upper()
    date = col2.date_input("Buy Date", datetime.date.today())
    col3, col4, col5 = st.columns(3)
    price = col3.number_input("Buy Price ($)", min_value=0.0)
    shares = col4.number_input("Shares", min_value=0.0, format="%.6f")
    sector_options = ['Technology', 'Healthcare', 'Financials', 'Energy', 'Utilities', 'Consumer Goods', 'Industrials', 'Materials', 'Other']
    sector = col5.selectbox("Sector", sector_options)
    submit = st.form_submit_button("💾 Add Trade")

    if submit:
        if ticker and shares > 0 and price > 0:
            new_row = pd.DataFrame({
                'Ticker': [ticker],
                'Date': [pd.to_datetime(date)],
                'Buy Price': [price],
                'Shares': [shares],
                'Sector': [sector]
            })
            df = pd.concat([df, new_row], ignore_index=True)
            set_with_dataframe(sheet, df)
            st.success(f"Added {shares} shares of {ticker}!")
        else:
            st.error("Please fill in all fields with valid values.")

# === PORTFOLIO LOGIC ===
if not df.empty:
    df['Ticker'] = df['Ticker'].str.upper()
    agg = df.groupby('Ticker').apply(
        lambda x: pd.Series({
            'Total Shares': x['Shares'].sum(),
            'Total Invested': (x['Shares'] * x['Buy Price']).sum(),
            'Avg Buy Price': (x['Shares'] * x['Buy Price']).sum() / x['Shares'].sum(),
            'Sector': x['Sector'].iloc[0]
        })
    ).reset_index()

    prices = {}
    for t in agg['Ticker']:
        try:
            prices[t] = yf.Ticker(t).history(period='1d')['Close'].iloc[-1]
        except:
            prices[t] = None

    agg['Current Price'] = agg['Ticker'].map(prices)
    agg['Market Value'] = agg['Current Price'] * agg['Total Shares']
    agg['P/L ($)'] = agg['Market Value'] - agg['Total Invested']
    agg['P/L (%)'] = (agg['P/L ($)'] / agg['Total Invested']) * 100
    total_invested = agg['Total Invested'].sum()
    agg['Portfolio %'] = (agg['Total Invested'] / total_invested) * 100

    total_value = agg['Market Value'].sum()
    profit = total_value - total_invested
    profit_pct = (profit / total_invested) * 100

    # === METRICS ===
    top1, top2, top3 = st.columns([2, 1, 1])
    with top1:
        st.markdown("### 💼 Portfolio Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Invested", f"${total_invested:,.2f}")
        c2.metric("Market Value", f"${total_value:,.2f}")
        c3.metric("Total P/L", f"${profit:,.2f}", f"{profit_pct:.2f}%")

    with top2:
        st.markdown("### 🧩 Sector Allocation")
        pie_data = agg.groupby('Sector')['Total Invested'].sum()
        fig1, ax1 = plt.subplots(figsize=(3, 3))
        ax1.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
        ax1.axis('equal')
        st.pyplot(fig1)

    with top3:
        st.markdown("### 📈 Sector P/L")
        sector_pl = agg.groupby('Sector')['P/L ($)'].sum()
        fig2, ax2 = plt.subplots(figsize=(3, 2))
        sector_pl.plot(kind='bar', ax=ax2, color='teal')
        ax2.set_ylabel("P/L ($)")
        ax2.set_title("Sector P/L")
        st.pyplot(fig2)

    # === PORTFOLIO TABLE ===
    st.subheader("🧾 Portfolio Overview")
    st.dataframe(agg.style.format({
        'Avg Buy Price': '${:.2f}',
        'Current Price': '${:.2f}',
        'Market Value': '${:.2f}',
        'Total Invested': '${:.2f}',
        'P/L ($)': '${:.2f}',
        'P/L (%)': '{:.2f}%',
        'Portfolio %': '{:.2f}%'
    }), use_container_width=True)
else:
    st.info("Add trades to get started.")
