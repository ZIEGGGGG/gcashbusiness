import streamlit as st
import pandas as pd
from datetime import datetime
import os
import math
from PIL import Image
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage

# ================= CONFIG =================
EXCEL_FILE = "GCash_Cash_In_Cash_Out_Record.xlsx"
UPLOAD_FOLDER = "uploads"
CAPITAL = 15000  # Starting capital

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

st.set_page_config(
    page_title="GCash Cash In / Cash Out Management System",
    page_icon="💙",
    layout="wide"
)

# ================= FUNCTIONS =================
def compute_service_fee(amount):
    return math.ceil(amount / 250) * 5 if amount > 0 else 0

def create_excel():
    df = pd.DataFrame(columns=[
        "Date", "Type", "Customer", "Amount", "Service Fee", "Screenshot", "Remarks"
    ])
    df.to_excel(EXCEL_FILE, index=False)
    return df

def save_with_images(df):
    df.to_excel(EXCEL_FILE, index=False)
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active

    for i, file in enumerate(df["Screenshot"], start=2):
        if isinstance(file, str) and file:
            path = os.path.join(UPLOAD_FOLDER, file)
            if os.path.exists(path):
                img = XLImage(path)
                img.width = img.height = 70
                ws.add_image(img, f"F{i}")
    wb.save(EXCEL_FILE)

def load_data():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        df.to_excel(EXCEL_FILE, index=False)
    else:
        df = create_excel()
    return df

# ================= LOAD DATA =================
df = load_data()

# ================= INITIALIZE BALANCES =================
if "gcash_balance" not in st.session_state:
    st.session_state.gcash_balance = CAPITAL
if "total_cash" not in st.session_state:
    st.session_state.total_cash = 0
if "total_profit" not in st.session_state:
    st.session_state.total_profit = 0

# ================= HEADER =================
st.title("💙 GCash Cash In / Cash Out System")

c1, c2, c3, c4 = st.columns(4)
c1.metric("💼 Capital", f"₱{CAPITAL:,.2f}")
c2.metric("💰 GCash Balance", f"₱{st.session_state.gcash_balance:,.2f}")
c3.metric("🤑 Total Cash Handed", f"₱{st.session_state.total_cash:,.2f}")
c4.metric("💵 Total Profit", f"₱{st.session_state.total_profit:,.2f}")

# ================= NAVIGATION =================
tab1, tab2, tab3 = st.tabs([
    "➕ New Transaction",
    "📋 Transaction History",
    "🗑 Delete (Admin)"
])

# ================= TAB 1 =================
with tab1:
    st.subheader("➕ New Transaction")
    with st.form("txn_form", clear_on_submit=True):
        txn_type = st.selectbox("Transaction Type", ["Cash In", "Cash Out"])
        customer = st.text_input("Customer Name")
        amount = st.number_input("Amount", min_value=1.0, step=1.0)
        fee = compute_service_fee(amount)  # Compute service fee
        st.info(f"Service Fee: ₱{fee}")
        screenshot = st.file_uploader("Upload Reference Screenshot", type=["jpg", "jpeg", "png"])
        remarks = st.text_input("Remarks (Optional)")
        submit = st.form_submit_button("💾 Save Transaction")

    if submit:
        if not customer or screenshot is None:
            st.error("❌ Customer name and screenshot are required.")
        else:
            filename = f"gcash_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            Image.open(screenshot).save(os.path.join(UPLOAD_FOLDER, filename))
            new_row = {
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Type": txn_type,
                "Customer": customer,
                "Amount": amount,
                "Service Fee": fee,
                "Screenshot": filename,
                "Remarks": remarks
            }

            # Update balances based on transaction type
            if txn_type == "Cash In":
                st.session_state.gcash_balance -= amount  # Decrease GCash balance
                st.session_state.total_cash += amount  # Increase total cash handed
                st.session_state.total_profit += fee  # Increase total profit by the service fee

            elif txn_type == "Cash Out":
                if amount > st.session_state.total_cash:
                    st.error("❌ Insufficient cash to cash out.")
                else:
                    st.session_state.gcash_balance += amount  # Increase GCash balance
                    st.session_state.total_cash -= amount  # Decrease total cash handed
                    # No effect on total profit for cash out
          
            # Add new transaction to the DataFrame
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_with_images(df)
            st.success("✅ Transaction saved")
            st.rerun()

# ================= TAB 2 =================
with tab2:
    st.subheader("📋 Transaction History")

    if df.empty:
        st.info("No transactions yet.")
    else:
        def thumb(file):
            if isinstance(file, str) and file:
                path = os.path.join(UPLOAD_FOLDER, file)
                if os.path.exists(path):
                    return f'<img src="{path}" width="60">'
            return ''

        view_df = df.copy()
        view_df["Screenshot"] = view_df["Screenshot"].apply(thumb)
        st.write(view_df.to_html(escape=False, index=False), unsafe_allow_html=True)

        st.download_button(
            "⬇ Download Excel",
            open(EXCEL_FILE, "rb"),
            file_name="GCash_Cash_In_Cash_Out_Record.xlsx"
        )

# ================= TAB 3 =================
with tab3:
    st.subheader("🗑 Delete Transaction (Admin Only)")
    if "admin" not in st.session_state:
        st.session_state.admin = False

    if not st.session_state.admin:
        u = st.text_input("Admin Username")
        p = st.text_input("Admin Password", type="password")

        if st.button("🔒 Login"):
            if u == "admin" and p == "adminpass":  # Change this for actual security
                st.session_state.admin = True
                st.success("Logged in")
                st.rerun()
            else:
                st.error("Invalid credentials")
    else:
        if df.empty:
            st.info("No transactions available to delete.")
        else:
            df["label"] = (
                df.index.astype(str) + " | " +
                df["Customer"].astype(str) + " | ₱" +
                df["Amount"].astype(str)
            )

            selected = st.selectbox("Select transaction", df["label"])
            confirm = st.checkbox("⚠ I confirm deletion")

            if st.button("❌ Delete Selected Transaction"):
                if confirm:
                    idx = int(selected.split(" | ")[0])
                    file = df.loc[idx, "Screenshot"]
                    transaction_type = df.loc[idx, "Type"]
                    amount = df.loc[idx, "Amount"]
                    service_fee = df.loc[idx, "Service Fee"]

                    if transaction_type == "Cash In":
                        st.session_state.total_cash -= amount   # Adjust total cash handed
                        st.session_state.total_profit -= service_fee  # Adjust total profit for cash-in transactions

                    elif transaction_type == "Cash Out":
                        st.session_state.total_cash += amount  # Return cash to total cash

                    if os.path.exists(file):
                        os.remove(file)

                    df.drop(index=idx, inplace=True)
                    df.reset_index(drop=True, inplace=True)
                    save_with_images(df)

                    st.success("✅ Transaction deleted")
                    st.rerun()
                else:
                    st.warning("Please confirm deletion first.")
