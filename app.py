
import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import os
import matplotlib.pyplot as plt
from google.oauth2 import service_account
from gspread_pandas import Spread, Client

# Google Sheets config
SHEET_NAME = "StockPortfolioData"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

# Load credentials from Streamlit secrets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES)
client = Client(scope=SCOPES, creds=credentials)
spread = Spread(SHEET_NAME, client=client)

# Initialize sheet headers if empty
existing_df = spread.sheet_to_df(index=None)
if existing_df.empty:
    headers = ['Ticker', 'Date', 'Buy Price', 'Shares', 'Sector', 'Type', 'Sell Price']
    spread.df_to_sheet(pd.DataFrame(columns=headers), index=False, replace=True)

# UI setup
st.set_page_config(page_title="Stock Portfolio Tracker", layout="wide", page_icon=":bar_chart:")
st.title("📈 Stock Portfolio Tracker")

# Form for new entry
with st.form("entry_form"):
    col1, col2 = st.columns(2)
    ticker = col1.text_input("Stock Ticker").strip().upper()
    date = col2.date_input("Buy Date", datetime.date.today())

    col3, col4, col5 = st.columns(3)
    price = col3.number_input("Buy Price ($)", min_value=0.0)
    shares = col4.number_input("Shares", min_value=0.0, format="%.6f")
    sector = col5.selectbox("Sector", ['Technology', 'Healthcare', 'Financials', 'Energy', 'Utilities', 'Consumer Goods', 'Industrials', 'Materials', 'Other'])

    col6, col7 = st.columns(2)
    trade_type = col6.selectbox("Trade Type", ["Buy", "Sell"])
    sell_price = col7.number_input("Sell Price (only for Sell)", min_value=0.0)

    submitted = st.form_submit_button("💾 Add Trade")
    if submitted and ticker and shares > 0 and price > 0:
        new_data = {
            'Ticker': ticker,
            'Date': date,
            'Buy Price': price,
            'Shares': shares,
            'Sector': sector,
            'Type': trade_type,
            'Sell Price': sell_price if trade_type == "Sell" else None
        }
        spread.append_row(list(new_data.values()))
        st.success(f"Added {trade_type} trade for {shares} shares of {ticker}!")

# Load latest data
df = spread.sheet_to_df(index=None)
if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'])
    df['Ticker'] = df['Ticker'].str.upper()
    df['Buy Price'] = pd.to_numeric(df['Buy Price'], errors='coerce')
    df['Sell Price'] = pd.to_numeric(df['Sell Price'], errors='coerce')
    df['Shares'] = pd.to_numeric(df['Shares'], errors='coerce')
    df['Type'] = df['Type'].fillna("Buy")

    buys = df[df['Type'] == 'Buy']
    sells = df[df['Type'] == 'Sell']

    # Aggregated holdings
    agg = buys.groupby('Ticker').apply(lambda x: pd.Series({
        'Total Shares': x['Shares'].sum(),
        'Total Invested': (x['Shares'] * x['Buy Price']).sum(),
        'Avg Buy Price': (x['Shares'] * x['Buy Price']).sum() / x['Shares'].sum(),
        'Sector': x['Sector'].iloc[0]
    })).reset_index()

    # Add market price
    prices = {}
    for t in agg['Ticker']:
        try:
            prices[t] = yf.Ticker(t).history(period='1d')['Close'].iloc[-1]
        except:
            prices[t] = None
    agg['Current Price'] = agg['Ticker'].map(prices)
    agg['Market Value'] = agg['Total Shares'] * agg['Current Price']
    agg['Unrealized P/L'] = agg['Market Value'] - agg['Total Invested']
    agg['Unrealized P/L (%)'] = (agg['Unrealized P/L'] / agg['Total Invested']) * 100

    # Calculate realized gain from sells
    sell_agg = sells.groupby('Ticker').apply(lambda x: pd.Series({
        'Realized Gain': (x['Shares'] * x['Sell Price']).sum() - (x['Shares'] * agg.loc[agg['Ticker'] == x.name, 'Avg Buy Price'].values[0] if x.name in agg['Ticker'].values else 0).sum()
    })).reset_index().rename(columns={0: 'Realized Gain'})

    agg = agg.merge(sell_agg, on='Ticker', how='left').fillna({'Realized Gain': 0})
    total_invested = agg['Total Invested'].sum()
    total_value = agg['Market Value'].sum()
    total_unrealized = agg['Unrealized P/L'].sum()
    total_realized = agg['Realized Gain'].sum()

    # Summary Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Invested", f"${total_invested:,.2f}")
    col2.metric("Market Value", f"${total_value:,.2f}")
    col3.metric("Unrealized P/L", f"${total_unrealized:,.2f}")
    col4.metric("Realized Gain", f"${total_realized:,.2f}")

    # Pie Chart by Sector
    st.markdown("### 📊 Sector Allocation")
    sector_alloc = agg.groupby('Sector')['Total Invested'].sum()
    fig1, ax1 = plt.subplots()
    ax1.pie(sector_alloc, labels=sector_alloc.index, autopct='%1.1f%%')
    ax1.axis('equal')
    st.pyplot(fig1)

    # P/L by Sector
    st.markdown("### 📈 Sector P/L")
    sector_pl = agg.groupby('Sector')['Unrealized P/L'].sum()
    fig2, ax2 = plt.subplots()
    sector_pl.plot(kind='bar', ax=ax2)
    ax2.set_ylabel("Unrealized P/L ($)")
    st.pyplot(fig2)

    # Table
    st.subheader("📋 Portfolio Table")
    st.dataframe(agg.style.format({
        'Avg Buy Price': '${:.2f}',
        'Current Price': '${:.2f}',
        'Total Invested': '${:.2f}',
        'Market Value': '${:.2f}',
        'Unrealized P/L': '${:.2f}',
        'Unrealized P/L (%)': '{:.2f}%',
        'Realized Gain': '${:.2f}'
    }), use_container_width=True)
else:
    st.info("Add trades to get started.")
