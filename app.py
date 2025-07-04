import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import yfinance as yf
import datetime
import matplotlib.pyplot as plt

# Google Sheets setup
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(credentials)
    sheet = client.open("StockPortfolioData").sheet1
except Exception as e:
    st.error(f"Failed to connect to Google Sheets: {e}")
    st.stop()

# Load data
@st.cache_data
def load_data():
    try:
        data = pd.DataFrame(sheet.get_all_records())
        if not data.empty:
            data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
            data = data.dropna(subset=['Date'])  # Remove rows with invalid dates
        return data
    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {e}")
        return pd.DataFrame(columns=['Ticker', 'Date', 'Action', 'Buy Price', 'Shares', 'Sell Price', 'Sector'])

data = load_data()

st.set_page_config(page_title="Stock Portfolio Tracker", layout="wide", page_icon="📈")
st.title("📊 Stock Portfolio Tracker")

# Entry form
with st.form("Add Entry"):
    st.subheader("💹 Add Trade")
    col1, col2 = st.columns(2)
    ticker = col1.text_input("Stock Ticker").strip().upper()
    date = col2.date_input("Buy Date", datetime.datetime.today())
    col3, col4, col5, col6 = st.columns(4)
    action = col3.selectbox("Action", ["Buy", "Sell"])
    price = col4.number_input("Price ($)", min_value=0.0, step=0.01)
    shares = col5.number_input("Shares", min_value=0.0, format="%.6f")
    sector_options = ['Technology', 'Healthcare', 'Financials', 'Energy', 'Utilities', 'Consumer Goods', 'Industrials', 'Materials', 'Other']
    sector = col6.selectbox("Sector", sector_options)
    submit = st.form_submit_button("💾 Add Trade")

    if submit:
        if ticker and shares > 0 and price > 0:
            try:
                buy_price = price if action == "Buy" else ""
                sell_price = price if action == "Sell" else ""
                sheet.append_row([ticker, str(date), action, buy_price, shares, sell_price, sector])
                st.success(f"Added {action} trade for {shares} shares of {ticker}!")
                st.experimental_rerun()  # Refresh to reload data
            except Exception as e:
                st.error(f"Error adding trade: {e}")
        else:
            st.error("Please fill in all fields with valid values.")

# Portfolio logic
if not data.empty:
    data['Ticker'] = data['Ticker'].str.upper()
    buys = data[data['Action'] == 'Buy'].copy()
    sells = data[data['Action'] == 'Sell'].copy()

    # Aggregate buys
    agg = buys.groupby('Ticker').apply(
        lambda x: pd.Series({
            'Total Shares': x['Shares'].sum(),
            'Total Invested': (x['Shares'] * x['Buy Price'].astype(float, errors='ignore')).sum(),
            'Avg Buy Price': (x['Shares'] * x['Buy Price'].astype(float, errors='ignore')).sum() / x['Shares'].sum() if x['Shares'].sum() > 0 else 0,
            'Sector': x['Sector'].iloc[0]
        })
    ).reset_index()

    # Aggregate sells
    sell_agg = sells.groupby('Ticker').agg({
        'Shares': 'sum',
        'Sell Price': lambda x: (x.astype(float, errors='ignore') * sells.loc[sells['Ticker'] == x.name, 'Shares']).sum() / sells.loc[sells['Ticker'] == x.name, 'Shares'].sum() if sells.loc[sells['Ticker'] == x.name, 'Shares'].sum() > 0 else 0
    }).rename(columns={'Shares': 'Sold Shares', 'Sell Price': 'Avg Sell Price'}).reset_index()

    # Merge buy and sell data
    agg = pd.merge(agg, sell_agg, on='Ticker', how='left').fillna({'Sold Shares': 0, 'Avg Sell Price': 0})
    agg['Remaining Shares'] = agg['Total Shares'] - agg['Sold Shares']
    agg = agg[agg['Remaining Shares'] > 0]

    # Fetch current prices
    prices = {}
    for t in agg['Ticker']:
        try:
            prices[t] = yf.Ticker(t).history(period='1d')['Close'].iloc[-1]
        except:
            prices[t] = None

    agg['Current Price'] = agg['Ticker'].map(prices)
    agg['Market Value'] = agg['Current Price'] * agg['Remaining Shares']
    agg['Unrealized P/L'] = agg['Market Value'] - agg['Total Invested']
    agg['Realized P/L'] = (agg['Avg Sell Price'] - agg['Avg Buy Price']) * agg['Sold Shares']
    agg['Total P/L'] = agg['Unrealized P/L'] + agg['Realized P/L']
    total_invested = agg['Total Invested'].sum()
    agg['Portfolio %'] = (agg['Market Value'] / agg['Market Value'].sum()) * 100

    total_value = agg['Market Value'].sum()
    profit = agg['Total P/L'].sum()
    profit_pct = (profit / total_invested) * 100 if total_invested > 0 else 0

    # --- Top Row: Metrics + Charts ---
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
        sector_pl = agg.groupby('Sector')['Total P/L'].sum()
        fig2, ax2 = plt.subplots(figsize=(3, 2))
        sector_pl.plot(kind='bar', ax=ax2, color='teal')
        ax2.set_ylabel("P/L ($)")
        ax2.set_title("Sector P/L")
        st.pyplot(fig2)

    # --- Portfolio Table ---
    st.subheader("🧾 Portfolio Overview")
    st.dataframe(agg.style.format({
        'Avg Buy Price': '${:.2f}',
        'Avg Sell Price': '${:.2f}',
        'Current Price': '${:.2f}',
        'Total Invested': '${:.2f}',
        'Market Value': '${:.2f}',
        'Unrealized P/L': '${:.2f}',
        'Realized P/L': '${:.2f}',
        'Total P/L': '${:.2f}',
        'Portfolio %': '{:.2f}%'
    }), use_container_width=True)

    # --- Editable Trade Section ---
    st.markdown("---")
    st.markdown("### ✏️ Edit or Delete a Trade")

    data['label'] = data.apply(lambda row: f"{row['Ticker']} - {row['Action']} {row['Shares']} @ ${row['Buy Price'] if row['Action'] == 'Buy' else row['Sell Price']} on {row['Date'].date()}", axis=1)
    selection = st.selectbox("Select Trade", data['label'].tolist())
    selected_index = data[data['label'] == selection].index[0]
    trade = data.loc[selected_index]

    edit_col1, edit_col2 = st.columns(2)
    new_ticker = edit_col1.text_input("Edit Ticker", trade['Ticker'])
    new_date = edit_col2.date_input("Edit Date", pd.to_datetime(trade['Date']))
    edit_col3, edit_col4, edit_col5, edit_col6 = st.columns(4)
    new_action = edit_col3.selectbox("Edit Action", ["Buy", "Sell"], index=0 if trade['Action'] == "Buy" else 1)
    new_price = edit_col4.number_input("Edit Price", value=float(trade['Buy Price'] if trade['Action'] == "Buy" else trade['Sell Price']), step=0.01)
    new_shares = edit_col5.number_input("Edit Shares", value=float(trade['Shares']), format="%.6f")
    new_sector = edit_col6.selectbox("Edit Sector", sector_options, index=sector_options.index(trade['Sector']) if trade['Sector'] in sector_options else 0)

    col_a, col_b = st.columns(2)
    if col_a.button("✅ Update Trade"):
        try:
            new_buy_price = new_price if new_action == "Buy" else ""
            new_sell_price = new_price if new_action == "Sell" else ""
            sheet.update_cell(selected_index + 2, 1, new_ticker.upper())
            sheet.update_cell(selected_index + 2, 2, str(new_date))
            sheet.update_cell(selected_index + 2, 3, new_action)
            sheet.update_cell(selected_index + 2, 4, new_buy_price)
            sheet.update_cell(selected_index + 2, 5, new_shares)
            sheet.update_cell(selected_index + 2, 6, new_sell_price)
            sheet.update_cell(selected_index + 2, 7, new_sector)
            st.success("Trade updated!")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Error updating trade: {e}")

    if col_b.button("🗑️ Delete Trade"):
        try:
            sheet.delete_rows(selected_index + 2)
            st.warning("Trade deleted!")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Error deleting trade: {e}")

else:
    st.info("Add trades to get started.")