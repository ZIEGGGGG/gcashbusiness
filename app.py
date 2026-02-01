import streamlit as st
import pandas as pd
from datetime import datetime
import os
from PIL import Image
import math
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage

# ================= CONFIG =================
EXCEL_FILE = "GCash_Cash_In_Cash_Out_Record.xlsx"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Admin credentials
ADMIN_USERNAME = "jepollogcash"
ADMIN_PASSWORD = "jepollogcash"

st.set_page_config(
    page_title="GCash Cash In / Cash Out System",
    page_icon="💙",
    layout="wide"
)

# ================= STYLE =================
st.markdown("""
<style>
body { background-color: #f5f9ff; }
.main { background-color: white; padding: 1rem; border-radius: 12px; }
h1, h2, h3 { color: #0057ff; }
.stButton > button {
    background-color: #0057ff;
    color: white;
    border-radius: 8px;
    height: 45px;
    font-weight: bold;
}
.stButton > button:hover { background-color: #0041cc; }
[data-testid="stFileUploaderDropzone"] { min-height: 3rem; }
</style>
""", unsafe_allow_html=True)

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

def save_with_images(df, excel_file):
    """Save Excel and embed screenshots"""
    df_copy = df.copy()
    df_copy.to_excel(excel_file, index=False, engine="openpyxl")
    wb = load_workbook(excel_file)
    ws = wb.active
    for i, filename in enumerate(df_copy["Reference Screenshot"], start=2):  # start=2 for header
        img_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(img_path):
            img = XLImage(img_path)
            img.width = 80
            img.height = 80
            ws.add_image(img, f"F{i}")  # column F = Reference Screenshot
    wb.save(excel_file)

def load_data():
    try:
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE, engine="openpyxl")
            # Remove old columns if exist
            for col in ["Total Received / Released", "Payment Method"]:
                if col in df.columns:
                    df.drop(columns=[col], inplace=True)
            df.to_excel(EXCEL_FILE, index=False, engine="openpyxl")
        else:
            df = create_excel()
    except Exception:
        df = create_excel()
    return df

# ================= LOAD DATA WITH SESSION STATE =================
if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# ================= SIDEBAR NAVIGATION =================
st.sidebar.title("💙 GCash System Navigation")
page = st.sidebar.radio(
    "Go to:",
    ["Transaction Form & History", "Admin Delete Transactions"]
)

# ================= PAGE 1: TRANSACTION FORM & HISTORY =================
if page == "Transaction Form & History":
    st.title("💙 GCash Cash In / Cash Out System")
    st.caption("Cashier transaction recording system")

    st.subheader("🧾 Transaction Form")
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

    if submit:
        if not transaction_type or not customer_name:
            st.error("❌ Please fill all required fields.")
        elif amount <= 0:
            st.error("❌ Amount must be greater than zero.")
        elif screenshot is None:
            st.error("❌ Reference screenshot is required.")
        else:
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

            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            save_with_images(st.session_state.df, EXCEL_FILE)
            st.success("✅ Transaction saved successfully!")
            st.experimental_rerun()

    # ================= TRANSACTION RECORDS =================
    st.subheader("📋 Transaction Records")
    if not st.session_state.df.empty:
        def make_thumbnail(filename):
            path = os.path.join(UPLOAD_FOLDER, filename)
            return f'<a href="{path}" target="_blank"><img src="{path}" width="80"></a>'

        display_df = st.session_state.df.copy()
        display_df["Reference Screenshot"] = display_df["Reference Screenshot"].apply(make_thumbnail)
        st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)

        # Download button
        st.download_button(
            label="⬇ Download Transaction Records as Excel",
            data=open(EXCEL_FILE, "rb").read(),
            file_name="GCash_Cash_In_Cash_Out_Record.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No transactions recorded yet.")

# ================= PAGE 2: ADMIN DELETE =================
elif page == "Admin Delete Transactions":
    st.title("🗑 Admin - Delete Transactions")
    if st.session_state.df.empty:
        st.info("No transactions available to delete.")
    else:
        username = st.text_input("Admin Username")
        password = st.text_input("Admin Password", type="password")
        login_button = st.button("🔒 Login for Delete")

        if login_button:
            if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
                st.error("❌ Invalid username or password")
            else:
                st.success("✅ Logged in successfully! You can now delete transactions.")

                st.session_state.df["__label"] = (
                    st.session_state.df.index.astype(str) + " | " +
                    st.session_state.df["Date"].astype(str) + " | " +
                    st.session_state.df["Customer Name"].astype(str) + " | ₱" +
                    st.session_state.df["Amount"].astype(str)
                )

                selected = st.selectbox(
                    "Select transaction to delete",
                    st.session_state.df["__label"].tolist()
                )

                confirm = st.checkbox("⚠ I confirm that I want to permanently delete this transaction")

                if st.button("❌ Delete Selected Transaction"):
                    if not confirm:
                        st.warning("Please confirm deletion first.")
                    else:
                        row_index = int(selected.split(" | ")[0])
                        screenshot_file = st.session_state.df.loc[row_index, "Reference Screenshot"]
                        screenshot_path = os.path.join(UPLOAD_FOLDER, screenshot_file)
                        if os.path.exists(screenshot_path):
                            os.remove(screenshot_path)

                        # Delete row from session_state df
                        st.session_state.df = st.session_state.df.drop(index=row_index).reset_index(drop=True)

                        # Save updated df to Excel
                        save_with_images(st.session_state.df, EXCEL_FILE)

                        st.success("✅ Transaction deleted successfully!")
                        st.experimental_rerun()
