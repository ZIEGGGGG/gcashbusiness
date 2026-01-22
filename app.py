import streamlit as st
import pandas as pd
from datetime import datetime
import os
from PIL import Image
import math

# ================= CONFIG =================
EXCEL_FILE = "GCash_Cash_In_Cash_Out_Record.xlsx"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

st.set_page_config(
    page_title="GCash Cash In / Cash Out",
    page_icon="💙",
    layout="centered"
)

# ================= STYLE =================
st.markdown("""
<style>
body { background-color: #f5f9ff; }
.main {
    background-color: white;
    padding: 2rem;
    border-radius: 12px;
}
h1, h2, h3 { color: #0057ff; }
.stButton > button {
    background-color: #0057ff;
    color: white;
    border-radius: 8px;
    height: 45px;
    font-weight: bold;
}
.stButton > button:hover {
    background-color: #0041cc;
}
</style>
""", unsafe_allow_html=True)

# ================= TITLE =================
st.title("💙 GCash Cash In / Cash Out")
st.caption("Cashier transaction recording system")

# ================= FUNCTIONS =================
def create_excel():
    df = pd.DataFrame(columns=[
        "Date",
        "Transaction Type",
        "Customer Name",
        "Amount",
        "Service Fee",
        "Reference Screenshot",
        "Remarks"
    ])
    df.to_excel(EXCEL_FILE, index=False, engine="openpyxl")
    return df

def compute_service_fee(amount):
    if amount <= 0:
        return 0
    return math.ceil(amount / 250) * 5

# ================= LOAD DATA SAFELY =================
try:
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE, engine="openpyxl")
        # Ensure old Total column is removed if exists
        if "Total Received / Released" in df.columns:
            df.drop(columns=["Total Received / Released"], inplace=True)
        if "Payment Method" in df.columns:
            df.drop(columns=["Payment Method"], inplace=True)
        df.to_excel(EXCEL_FILE, index=False, engine="openpyxl")
    else:
        df = create_excel()
except Exception:
    df = create_excel()

# ================= FORM =================
st.subheader("🧾 Cashier Transaction Form")

with st.form("cashier_form"):
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.text_input("Date & Time", value=current_datetime, disabled=True)

    transaction_type = st.selectbox(
        "Transaction Type *",
        ["", "Cash In", "Cash Out"]
    )

    customer_name = st.text_input("Customer Name *")

    amount = st.number_input(
        "Amount *",
        min_value=0.0,
        step=1.0,
        format="%.2f"
    )

    service_fee = compute_service_fee(amount)
    st.number_input(
        "Service Fee (Auto-calculated)",
        value=float(service_fee),
        disabled=True
    )
    st.caption("💡 Service Fee: ₱5 for every ₱250 (or part of ₱250)")

    screenshot = st.file_uploader(
        "Upload Reference Screenshot *",
        type=["jpg", "jpeg", "png"]
    )

    remarks = st.text_input("Remarks (Optional)")

    submit = st.form_submit_button("💾 Save Transaction")

# ================= VALIDATION & SAVE =================
if submit:
    if not transaction_type or not customer_name:
        st.error("❌ Please fill all required fields.")
    elif amount <= 0:
        st.error("❌ Amount must be greater than zero.")
    elif screenshot is None:
        st.error("❌ Reference screenshot is required.")
    else:
        # Save screenshot
        filename = f"gcash_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        Image.open(screenshot).save(filepath)

        new_row = {
            "Date": current_datetime,
            "Transaction Type": transaction_type,
            "Customer Name": customer_name,
            "Amount": amount,
            "Service Fee": service_fee,
            "Reference Screenshot": filename,
            "Remarks": remarks
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(EXCEL_FILE, index=False, engine="openpyxl")

        st.success("✅ Transaction saved successfully!")
        st.rerun()

# ================= RECORDS =================
st.subheader("📋 Transaction Records")

# Show screenshot as clickable link
def make_clickable(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    return f"[View Screenshot]({path})"

if not df.empty:
    display_df = df.copy()
    display_df["Reference Screenshot"] = display_df["Reference Screenshot"].apply(make_clickable)
    st.dataframe(display_df, use_container_width=True)
