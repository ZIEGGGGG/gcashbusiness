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

def load_data():
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE, engine="openpyxl")
    return create_excel()

def compute_service_fee(amount):
    return math.ceil(amount / 250) * 5 if amount > 0 else 0

def save_with_images(df):
    df.to_excel(EXCEL_FILE, index=False, engine="openpyxl")
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active

    for i, file in enumerate(df["Reference Screenshot"], start=2):
        path = os.path.join(UPLOAD_FOLDER, str(file))
        if os.path.exists(path):
            img = XLImage(path)
            img.width = img.height = 80
            ws.add_image(img, f"F{i}")

    wb.save(EXCEL_FILE)

# ================= SESSION STATE =================
if "df" not in st.session_state:
    st.session_state.df = load_data()

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# ================= SIDEBAR =================
st.sidebar.title("💙 GCash System")
page = st.sidebar.radio(
    "Navigation",
    ["Transaction Form & History", "Admin Delete Transactions"]
)

# ================= PAGE 1 =================
if page == "Transaction Form & History":
    st.title("💙 GCash Cash In / Cash Out")

    with st.form("transaction_form"):
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.text_input("Date & Time", value=date_now, disabled=True)

        t_type = st.selectbox("Transaction Type *", ["", "Cash In", "Cash Out"])
        name = st.text_input("Customer Name *")
        amount = st.number_input("Amount *", min_value=0.0, step=1.0)

        fee = compute_service_fee(amount)
        st.number_input("Service Fee", value=fee, disabled=True)

        screenshot = st.file_uploader("Reference Screenshot *", ["jpg", "png", "jpeg"])
        remarks = st.text_input("Remarks")

        submit = st.form_submit_button("💾 Save Transaction")

    if submit:
        if not t_type or not name or amount <= 0 or not screenshot:
            st.error("❌ Please complete all required fields")
        else:
            filename = f"gcash_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            Image.open(screenshot).save(os.path.join(UPLOAD_FOLDER, filename))

            new_row = {
                "Date": date_now,
                "Transaction Type": t_type,
                "Customer Name": name,
                "Amount": amount,
                "Service Fee": fee,
                "Reference Screenshot": filename,
                "Remarks": remarks
            }

            st.session_state.df = pd.concat(
                [st.session_state.df, pd.DataFrame([new_row])],
                ignore_index=True
            )

            save_with_images(st.session_state.df)
            st.success("✅ Transaction saved")
            st.rerun()

    st.subheader("📋 Transaction History")

    if not st.session_state.df.empty:
        def thumb(x):
            p = os.path.join(UPLOAD_FOLDER, str(x))
            return f'<img src="{p}" width="70">' if os.path.exists(p) else ""

        view_df = st.session_state.df.copy()
        view_df["Reference Screenshot"] = view_df["Reference Screenshot"].apply(thumb)
        st.write(view_df.to_html(escape=False, index=False), unsafe_allow_html=True)

        st.download_button(
            "⬇ Download Excel",
            open(EXCEL_FILE, "rb").read(),
            file_name=EXCEL_FILE
        )
    else:
        st.info("No transactions yet")

# ================= PAGE 2 =================
else:
    st.title("🗑 Admin Delete Transactions")

    if not st.session_state.admin_logged_in:
        user = st.text_input("Admin Username")
        pwd = st.text_input("Admin Password", type="password")

        if st.button("🔒 Login"):
            if user == ADMIN_USERNAME and pwd == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.success("✅ Logged in")
                st.rerun()
            else:
                st.error("❌ Invalid credentials")
    else:
        st.success("✅ Admin Logged In")

        labels = (
            st.session_state.df.index.astype(str)
            + " | "
            + st.session_state.df["Date"]
            + " | "
            + st.session_state.df["Customer Name"]
            + " | ₱"
            + st.session_state.df["Amount"].astype(str)
        )

        choice = st.selectbox("Select transaction", labels)
        confirm = st.checkbox("⚠ Confirm permanent deletion")

        if st.button("❌ Delete"):
            if not confirm:
                st.warning("Please confirm deletion")
            else:
                idx = int(choice.split(" | ")[0])
                file = st.session_state.df.loc[idx, "Reference Screenshot"]
                path = os.path.join(UPLOAD_FOLDER, str(file))
                if os.path.exists(path):
                    os.remove(path)

                st.session_state.df = (
                    st.session_state.df.drop(idx).reset_index(drop=True)
                )

                save_with_images(st.session_state.df)
                st.success("✅ Deleted successfully")
                st.rerun()

        if st.button("🚪 Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()
