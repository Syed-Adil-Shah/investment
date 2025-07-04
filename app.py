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
    df = pd.DataFrame(columns=['Ticker', 'Date', 'Buy Price', 'Shares', 'Sector', 'Trade Type', 'Realized Gain'])

st.title("📊 Stock Portfolio Tracker")

# Entry form
with st.form("Add Entry"):
    col1, col2 = st.columns(2)
    ticker = col1.text_input("Stock Ticker").strip().upper()
    date = col2.date_input("Trade Date", datetime.date.today())
    col3, col4, col5 = st.columns(3)
    price = col3.number_input("Trade Price ($)", min_value=0.0)
    shares = col4.number_input("Shares", min_value=0.0, format="%.6f")
    trade_type = col5.selectbox("Trade Type", ['Buy', 'Sell'])
    col6, col7 = st.columns(2)
    sector_options = ['Technology', 'Healthcare', 'Financials', 'Energy', 'Utilities', 'Consumer Goods', 'Industrials', 'Materials', 'Other']
    sector = col6.selectbox("Sector", sector_options)
    submit = st.form_submit_button("📂 Add Trade")

    if submit:
        if ticker and shares > 0 and price > 0:
            realized_gain = 0
            if trade_type == 'Sell':
                # Calculate realized gain based on FIFO
                buy_df = df[(df['Ticker'] == ticker) & (df['Trade Type'] == 'Buy')].copy()
                buy_df.sort_values(by='Date', inplace=True)
                remaining = shares
                gain = 0
                for i, row in buy_df.iterrows():
                    if remaining <= 0:
                        break
                    lot_shares = min(row['Shares'], remaining)
                    gain += lot_shares * (price - row['Buy Price'])
                    remaining -= lot_shares
                realized_gain = gain

            new_row = pd.DataFrame({
                'Ticker': [ticker],
                'Date': [pd.to_datetime(date)],
                'Buy Price': [price],
                'Shares': [shares],
                'Sector': [sector],
                'Trade Type': [trade_type],
                'Realized Gain': [realized_gain if trade_type == 'Sell' else 0]
            })
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success(f"Added {trade_type} of {shares} shares of {ticker}!")
        else:
            st.error("Please fill in all fields with valid values.")

# Portfolio logic
if not df.empty:
    df['Ticker'] = df['Ticker'].str.upper()
    buy_df = df[df['Trade Type'] == 'Buy']
    sell_df = df[df['Trade Type'] == 'Sell']

    agg = buy_df.groupby('Ticker').apply(
        lambda x: pd.Series({
            'Total Shares': x['Shares'].sum(),
            'Total Invested': (x['Shares'] * x['Buy Price']).sum(),
            'Avg Buy Price': (x['Shares'] * x['Buy Price']).sum() / x['Shares'].sum(),
            'Sector': x['Sector'].iloc[0]
        })
    ).reset_index()

    sell_shares = sell_df.groupby('Ticker')['Shares'].sum()
    agg['Sold Shares'] = agg['Ticker'].map(sell_shares).fillna(0)
    agg['Remaining Shares'] = agg['Total Shares'] - agg['Sold Shares']

    prices = {}
    for t in agg['Ticker']:
        try:
            prices[t] = yf.Ticker(t).history(period='1d')['Close'].iloc[-1]
        except:
            prices[t] = None

    agg['Current Price'] = agg['Ticker'].map(prices)
    agg['Market Value'] = agg['Current Price'] * agg['Remaining Shares']
    agg['Unrealized Gain ($)'] = (agg['Current Price'] - agg['Avg Buy Price']) * agg['Remaining Shares']
    agg['Realized Gain ($)'] = df[df['Trade Type'] == 'Sell'].groupby('Ticker')['Realized Gain'].sum().reindex(agg['Ticker']).fillna(0).values
    agg['Total Gain ($)'] = agg['Unrealized Gain ($)'] + agg['Realized Gain ($)']

    total_invested = agg['Total Invested'].sum()
    total_value = agg['Market Value'].sum()
    total_realized = agg['Realized Gain ($)'].sum()
    total_unrealized = agg['Unrealized Gain ($)'].sum()
    total_gain = total_realized + total_unrealized
    profit_pct = (total_gain / total_invested) * 100

    agg['Portfolio %'] = (agg['Total Invested'] / total_invested) * 100

    # --- Top Row: Metrics + Charts ---
    top1, top2, top3 = st.columns([2, 1, 1])

    with top1:
        st.markdown("### 💼 Portfolio Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Invested", f"${total_invested:,.2f}")
        c2.metric("Market Value", f"${total_value:,.2f}")
        c3.metric("Total Gain", f"${total_gain:,.2f}", f"{profit_pct:.2f}%")
        st.markdown(f"**Realized Gain:** ${total_realized:,.2f}  ")
        st.markdown(f"**Unrealized Gain:** ${total_unrealized:,.2f}")

    with top2:
        st.markdown("### 🧩 Sector Allocation")
        pie_data = agg.groupby('Sector')['Total Invested'].sum()
        fig1, ax1 = plt.subplots(figsize=(3, 3))
        ax1.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
        ax1.axis('equal')
        st.pyplot(fig1)

    with top3:
        st.markdown("### 📈 Sector P/L")
        sector_pl = agg.groupby('Sector')['Total Gain ($)'].sum()
        fig2, ax2 = plt.subplots(figsize=(3, 2))
        sector_pl.plot(kind='bar', ax=ax2, color='teal')
        ax2.set_ylabel("P/L ($)")
        ax2.set_title("Sector P/L")
        st.pyplot(fig2)

    # --- Portfolio Table ---
    st.subheader("🧾 Portfolio Overview")
    st.dataframe(agg.style.format({
        'Avg Buy Price': '${:.2f}',
        'Current Price': '${:.2f}',
        'Market Value': '${:.2f}',
        'Total Invested': '${:.2f}',
        'Unrealized Gain ($)': '${:.2f}',
        'Realized Gain ($)': '${:.2f}',
        'Total Gain ($)': '${:.2f}',
        'Portfolio %': '{:.2f}%'
    }), use_container_width=True)

else:
    st.info("Add trades to get started.")
