
import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import matplotlib.pyplot as plt
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Stock Portfolio Tracker", layout="wide", page_icon="📈")

SHEET_ID = "12Aje52kDt7nh0uk4aLpPyaYiVMivQrornyuwUP3bJew"
SHEET_NAME = "Sheet1"

# Auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# Load sheet data
try:
    df = get_as_dataframe(sheet, evaluate_formulas=True).dropna(how='all')
    df['Date'] = pd.to_datetime(df['Date'])
except:
    df = pd.DataFrame(columns=['Type', 'Ticker', 'Date', 'Buy Price', 'Sell Price', 'Shares', 'Sector'])

st.title("📊 Stock Portfolio Tracker")

# Entry form
with st.form("Add Entry"):
    col1, col2 = st.columns(2)
    trade_type = col1.selectbox("Type", ["Buy", "Sell"])
    ticker = col2.text_input("Stock Ticker").strip().upper()
    date = st.date_input("Date", datetime.date.today())

    col3, col4, col5 = st.columns(3)
    buy_price = col3.number_input("Buy Price ($)", min_value=0.0)
    sell_price = col4.number_input("Sell Price ($)", min_value=0.0)
    shares = col5.number_input("Shares", min_value=0.0, format="%.6f")

    sector_options = ['Technology', 'Healthcare', 'Financials', 'Energy', 'Utilities', 'Consumer Goods', 'Industrials', 'Materials', 'Other']
    sector = st.selectbox("Sector", sector_options)

    submit = st.form_submit_button("💾 Add Trade")

    if submit:
        if ticker and shares > 0:
            new_row = pd.DataFrame({
                'Type': [trade_type],
                'Ticker': [ticker],
                'Date': [pd.to_datetime(date)],
                'Buy Price': [buy_price],
                'Sell Price': [sell_price],
                'Shares': [shares],
                'Sector': [sector]
            })
            df = pd.concat([df, new_row], ignore_index=True)
            sheet.clear()
            set_with_dataframe(sheet, df)
            st.success(f"{trade_type} {shares} shares of {ticker} recorded!")
        else:
            st.error("Fill all values properly.")

if not df.empty:
    df['Ticker'] = df['Ticker'].str.upper()

    buys = df[df['Type'] == 'Buy'].copy()
    sells = df[df['Type'] == 'Sell'].copy()

    # Grouped data for portfolio
    agg = buys.groupby('Ticker').apply(lambda x: pd.Series({
        'Total Bought Shares': x['Shares'].sum(),
        'Total Invested': (x['Shares'] * x['Buy Price']).sum(),
        'Avg Buy Price': (x['Shares'] * x['Buy Price']).sum() / x['Shares'].sum(),
        'Sector': x['Sector'].iloc[0]
    })).reset_index()

    sell_agg = sells.groupby('Ticker').apply(lambda x: pd.Series({
        'Total Sold Shares': x['Shares'].sum(),
        'Total Realized': (x['Shares'] * x['Sell Price']).sum(),
        'Realized Gain': (x['Shares'] * x['Sell Price']).sum() - (x['Shares'] * x['Buy Price']).sum()
    })).reset_index()

    agg = agg.merge(sell_agg, on='Ticker', how='left').fillna(0)

    prices = {}
    for t in agg['Ticker']:
        try:
            prices[t] = yf.Ticker(t).history(period='1d')['Close'].iloc[-1]
        except:
            prices[t] = None

    agg['Current Price'] = agg['Ticker'].map(prices)
    agg['Remaining Shares'] = agg['Total Bought Shares'] - agg['Total Sold Shares']
    agg['Market Value'] = agg['Remaining Shares'] * agg['Current Price']
    agg['Unrealized Gain'] = agg['Market Value'] - (agg['Avg Buy Price'] * agg['Remaining Shares'])

    total_realized = agg['Realized Gain'].sum()
    total_unrealized = agg['Unrealized Gain'].sum()
    total_invested = agg['Total Invested'].sum()
    total_value = agg['Market Value'].sum()

    st.subheader("💼 Portfolio Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Invested", f"${total_invested:,.2f}")
    c2.metric("Total Market Value", f"${total_value:,.2f}")
    c3.metric("Total Unrealized Gain", f"${total_unrealized:,.2f}")

    st.metric("Total Realized Gain", f"${total_realized:,.2f}")

    st.subheader("📋 Portfolio Overview")
    st.dataframe(agg[[
        'Ticker', 'Sector', 'Total Bought Shares', 'Total Sold Shares', 'Remaining Shares',
        'Avg Buy Price', 'Current Price', 'Total Invested',
        'Market Value', 'Unrealized Gain', 'Realized Gain'
    ]].style.format({
        'Avg Buy Price': '${:.2f}',
        'Current Price': '${:.2f}',
        'Total Invested': '${:.2f}',
        'Market Value': '${:.2f}',
        'Unrealized Gain': '${:.2f}',
        'Realized Gain': '${:.2f}'
    }), use_container_width=True)
else:
    st.info("Add some trades to get started.")
