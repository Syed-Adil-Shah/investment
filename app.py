import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Define the scope
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Use secrets stored in Streamlit
credentials_dict = st.secrets["gspread"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
gc = gspread.authorize(credentials)

# Open the Google Sheet
sheet = gc.open("StockPortfolioData").worksheet("Portfolio")

st.title("📊 Personal Stock Portfolio Tracker")

# Load existing data
@st.cache_data(ttl=60)
def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df = load_data()

# Add new trade
st.subheader("➕ Add Trade")
with st.form("trade_form"):
    ticker = st.text_input("Ticker").upper()
    date = st.date_input("Date")
    price = st.number_input("Buy Price", min_value=0.0)
    shares = st.number_input("Shares", min_value=0.0, format="%.4f")
    sector = st.text_input("Sector")
    action = st.selectbox("Action", ["Buy", "Sell"])
    submit = st.form_submit_button("Add")

    if submit and ticker and price and shares:
        new_row = [ticker, str(date), action, price, shares, sector]
        sheet.append_row(new_row)
        st.success("Trade added successfully!")
        st.cache_data.clear()

# Display data
st.subheader("📈 Portfolio")
st.dataframe(df)