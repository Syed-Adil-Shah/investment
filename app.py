
import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# Set page config
st.set_page_config(page_title="Stock Portfolio Tracker", layout="wide", page_icon="📈")

# Google Sheets Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("12Aje52kDt7nh0uk4aLpPyaYiVMivQrornyuwUP3bJew")
worksheet = spreadsheet.get_worksheet(0)

# Load data from sheet
df = get_as_dataframe(worksheet, evaluate_formulas=True, dtype=str)
df = df.dropna(how="all")  # Remove empty rows
if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'])
    df['Shares'] = df['Shares'].astype(float)
    df['Buy Price'] = pd.to_numeric(df.get('Buy Price', 0), errors='coerce').fillna(0)
    df['Sell Price'] = pd.to_numeric(df.get('Sell Price', 0), errors='coerce').fillna(0)

# --- Title
st.title("📊 Stock Portfolio Tracker")

# --- Add Trade Form
with st.form("add_trade_form"):
    col1, col2 = st.columns(2)
    action = col1.selectbox("Type", ["Buy", "Sell"])
    ticker = col2.text_input("Ticker").upper().strip()

    col3, col4 = st.columns(2)
    buy_price = col3.number_input("Buy Price", min_value=0.0)
    sell_price = col4.number_input("Sell Price", min_value=0.0)

    shares = st.number_input("Shares", min_value=0.0)
    date = st.date_input("Date", datetime.date.today())
    sector = st.selectbox("Sector", ['Technology', 'Healthcare', 'Financials', 'Energy', 'Utilities', 'Consumer Goods', 'Industrials', 'Materials', 'Other'])

    submitted = st.form_submit_button("➕ Add Trade")

    if submitted and ticker and shares > 0:
        new_entry = pd.DataFrame({
            'Type': [action],
            'Ticker': [ticker],
            'Date': [pd.to_datetime(date)],
            'Buy Price': [buy_price],
            'Sell Price': [sell_price],
            'Shares': [shares],
            'Sector': [sector]
        })
        df = pd.concat([df, new_entry], ignore_index=True)
        worksheet.clear()
        set_with_dataframe(worksheet, df)
        st.success(f"{action} trade added for {ticker}.")

# --- Portfolio Summary
if not df.empty:
    buys = df[df['Type'] == 'Buy'].copy()
    sells = df[df['Type'] == 'Sell'].copy()

    buy_agg = buys.groupby('Ticker', as_index=False).apply(lambda x: pd.Series({
        'Total Buy Shares': x['Shares'].sum(),
        'Total Invested': (x['Shares'] * x['Buy Price']).sum(),
        'Avg Buy Price': (x['Shares'] * x['Buy Price']).sum() / x['Shares'].sum(),
        'Sector': x['Sector'].iloc[0]
    })).reset_index(drop=True)

    sell_agg = sells.groupby('Ticker', as_index=False).apply(lambda x: pd.Series({
        'Total Sell Shares': x['Shares'].sum(),
        'Total Realized Gain': (x['Shares'] * x['Sell Price']).sum() - (x['Shares'] * x['Buy Price']).sum()
    })).reset_index(drop=True)

    if not buy_agg.empty and not sell_agg.empty:
        agg = pd.merge(buy_agg, sell_agg, on="Ticker", how="left").fillna(0)
    else:
        agg = buy_agg.copy()
        for col in ['Total Sell Shares', 'Total Realized Gain']:
            if col not in agg.columns:
                agg[col] = 0.0

    prices = {}
    for t in agg['Ticker']:
        try:
            prices[t] = yf.Ticker(t).history(period='1d')['Close'].iloc[-1]
        except:
            prices[t] = None

    agg['Current Price'] = agg['Ticker'].map(prices)
    agg['Unrealized Value'] = agg['Current Price'] * (agg['Total Buy Shares'] - agg['Total Sell Shares'])
    agg['Unrealized Gain'] = agg['Unrealized Value'] - (agg['Avg Buy Price'] * (agg['Total Buy Shares'] - agg['Total Sell Shares']))
    agg['Market Value'] = agg['Current Price'] * agg['Total Buy Shares']
    agg['Total Gain'] = agg['Total Realized Gain'] + agg['Unrealized Gain']

    st.subheader("📈 Portfolio Summary")
    st.dataframe(agg.style.format({
        'Total Invested': '${:.2f}',
        'Avg Buy Price': '${:.2f}',
        'Current Price': '${:.2f}',
        'Unrealized Value': '${:.2f}',
        'Unrealized Gain': '${:.2f}',
        'Total Realized Gain': '${:.2f}',
        'Total Gain': '${:.2f}',
        'Market Value': '${:.2f}'
    }), use_container_width=True)

else:
    st.info("No trades yet. Add some using the form above.")
