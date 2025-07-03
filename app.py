
import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import os
import matplotlib.pyplot as plt

DATA_FILE = 'portfolio_data.csv'
st.set_page_config(page_title="Stock Portfolio Tracker", layout="wide", page_icon="📈")

# Load or initialize data
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE, parse_dates=['Date'])
else:
    df = pd.DataFrame(columns=['Ticker', 'Date', 'Buy Price', 'Shares', 'Sector'])

# --- UI: Entry Form ---
st.title("📊 Stock Portfolio Tracker")
st.markdown("Dark-themed minimal portfolio tracker")

with st.form("Add Entry"):
    col1, col2 = st.columns(2)
    ticker = col1.text_input("Stock Ticker").upper()
    date = col2.date_input("Buy Date", datetime.date.today())
    col3, col4, col5 = st.columns(3)
    price = col3.number_input("Buy Price ($)", min_value=0.0)
    shares = col4.number_input("Shares", min_value=0)
    sector_options = ['Technology', 'Healthcare', 'Financials', 'Energy', 'Utilities', 'Consumer Goods', 'Industrials', 'Materials', 'Other']
    sector = col5.selectbox("Sector", sector_options)
    submit = st.form_submit_button("💾 Add Trade")

    if submit and ticker and shares > 0:
        df = pd.concat([df, pd.DataFrame([[ticker, date, price, shares, sector]], columns=df.columns)], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.success(f"Added {shares} shares of {ticker}!")

# --- Portfolio Aggregation ---
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

    # Fetch latest prices
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

    # --- Display Data ---
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

    # --- Summary Metrics ---
    total_value = agg['Market Value'].sum()
    profit = total_value - total_invested
    profit_pct = (profit / total_invested) * 100

    st.markdown("### 💼 Portfolio Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Invested", f"${total_invested:,.2f}")
    c2.metric("Market Value", f"${total_value:,.2f}")
    c3.metric("Total P/L", f"${profit:,.2f}", f"{profit_pct:.2f}%")

    # --- Charts ---
    st.markdown("### 🧩 Sector Allocation (Pie)")
    pie_data = agg.groupby('Sector')['Total Invested'].sum()
    fig1, ax1 = plt.subplots()
    ax1.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
    ax1.axis('equal')
    st.pyplot(fig1)

    st.markdown("### 📈 Sector-wise Profit / Loss")
    sector_pl = agg.groupby('Sector')['P/L ($)'].sum()
    fig2, ax2 = plt.subplots()
    sector_pl.plot(kind='bar', ax=ax2, color='teal')
    ax2.set_ylabel("P/L ($)")
    ax2.set_title("Sector Profit / Loss")
    st.pyplot(fig2)

else:
    st.info("Add trades to get started.")
