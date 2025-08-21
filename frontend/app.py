import streamlit as st
import requests

BASE_URL = "http://0.0.0.0:8000"

st.set_page_config(page_title="BTO Prediction")

st.title("BTO Price Prediction")

st.sidebar.title("API Endpoints")
endpoint = st.sidebar.selectbox(
    "Select API Endpoint:",
    [
        "AI Chat",
        "BTO Price Prediction"
    ]
)

def make_api_call(method, endpoint, data=None, params=None):
    try:
        url = f"{BASE_URL}/{endpoint}"
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            if isinstance(data, str):
                response = requests.post(url, data=data, headers={"Content-Type": "text/plain"})
            else:
                response = requests.post(url, json=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        return f"Connection error: {str(e)}"

if endpoint == "AI Chat":
    st.header("AI Chat for Analysis")
    st.markdown("Possible questions include:")
    st.markdown("1. Please recommend housing estates that have had limited BTO launches in the past ten years.")
    st.markdown("2. How much would a 4-room BTO flat cost in Tampines and what income do I need?")
    st.markdown("3. Please recommend housing estates that have had limited BTO launches in the past ten years. For each estate, provide an analysis of potential BTO prices for both 3-room and 4-room flats, considering low, middle, and high floor levels.")
    st.markdown("4. What are the BTO prospects and prices in Sengkang?")
    prompt = st.text_area(
        "Enter your question about BTOs:",
        value=st.session_state.get('chat_prompt', ''),
    )
    if st.button("Send"):
        if prompt:
            with st.spinner("analysing..."):
                result = make_api_call("POST", "/chat", data=prompt)
            st.success("Response:")
            st.markdown(result["response"])
        else:
            st.warning("Please enter a prompt")

elif endpoint == "BTO Price Prediction":
    st.header("BTO Price Prediction")
    
    storey = st.number_input("Storey", min_value=1, max_value=40, value=10)
    floor_area = st.number_input("Floor Area (sqm)", min_value=30, max_value=200, value=50)
    remaining_lease = st.number_input("Remaining Lease (years)", min_value=10, max_value=99, value=99)
    town = st.selectbox("Town", [
        "ANG MO KIO", "BEDOK", "BISHAN", "BUKIT BATOK", "BUKIT MERAH", 
        "BUKIT PANJANG", "BUKIT TIMAH", "CENTRAL AREA", "CHOA CHU KANG",
        "CLEMENTI", "GEYLANG", "HOUGANG", "JURONG EAST", "JURONG WEST",
        "KALLANG/WHAMPOA", "MARINE PARADE", "PASIR RIS", "PUNGGOL",
        "QUEENSTOWN", "SEMBAWANG", "SENGKANG", "SERANGOON", "TAMPINES",
        "TOA PAYOH", "WOODLANDS", "YISHUN"
    ])
    flat_type = st.selectbox("Flat Type", [
        "3 ROOM", "4 ROOM", "5 ROOM", "EXECUTIVE"
    ])
    
    if st.button("Predict Price"):
        data = {
            "storey_median": storey,
            "floor_area_sqm": floor_area,
            "remaining_lease": remaining_lease,
            "town": town,
            "flat_type": flat_type
        }
        result = make_api_call("POST", "/bto_price", data=data)
        
        st.success(f"Predicted Resale Price: **${result}**")