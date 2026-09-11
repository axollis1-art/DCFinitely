"""Streamlit entry point for the DCFinitely valuation platform."""

import streamlit as st


st.set_page_config(page_title="DCFinitely", page_icon="📈", layout="wide")

st.title("DCFinitely")
st.caption("Transparent discounted cash flow valuation for public companies.")

st.info(
    "The valuation engine and financial-data provider are under development. "
    "Use this entry point to verify the local Streamlit environment."
)

with st.sidebar:
    st.header("Valuation inputs")
    st.text_input("Ticker", placeholder="e.g. AAPL", disabled=True)

st.subheader("Getting started")
st.write(
    "The initial repository foundation is ready. Subsequent milestones will add "
    "financial data, forecast assumptions, and the DCF valuation workflow."
)
