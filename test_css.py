import streamlit as st

st.set_page_config(page_title="CSS Test", layout="wide")

st.markdown("""
<style>
body { background-color: red; }
h1 { color: blue; font-family: monospace; }
</style>
""", unsafe_allow_html=True)

st.title("Test Heading")
st.write("If this background is red and heading is blue monospace, CSS injection works.")