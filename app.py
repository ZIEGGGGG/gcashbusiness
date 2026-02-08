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
    else:
        df = create_excel()
    
    expected_cols = ["Date", "Type", "Customer", "Amount", "Service Fee", "Screenshot", "Remarks"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
    return df

def recalc_balances(df):
    total_cash = 0
    total_profit = 0
    
    for _, row in df.iterrows():
        txn_type = row.get("Type", "")
        amount = row.get("Amount", 0)
        fee = row.get("Service Fee", 0)
        
        if pd.isna(txn_type) or pd.isna(amount):
            continue
        
        if txn_type == "Cash In":
            total_cash += amount  # Sum total cash in
            total_profit += fee    # Increment profit by service fee for cash in
        elif txn_type == "Cash Out":
            if total_cash >= amount:
                total_cash -= amount  # Deduct cash out if sufficient
                total_profit += fee     # Increment profit by service fee for cash out

    gcash_balance = CAPITAL - total_cash  # Calculate GCash balance
    return gcash_balance, total_cash, total_profit

# ================= LOAD DATA =================
df = load_data()

# ================= INITIALIZE BALANCES =================
if "gcash_balance" not in st.session_state or \
   "total_cash" not in st.session_state or \
   "total_profit" not in st.session_state:
    st.session_state.gcash_balance, st.session_state.total_cash, st.session_state.total_profit = recalc_balances(df)

# ================= HEADER =================
st.title("💙 GCash Cash In / Cash Out System")
c1, c2, c3, c4 = st.columns(4)
c1.metric("💼 Capital", f"₱{CAPITAL:,.2f}")
c2.metric("💰 GCash Balance", f"₱{CAPITAL - st.session_state.total_cash:,.2f}")  # GCash balance calculation
c3.metric("🤑 Total Cash Handed", f"₱{st.session_state.total_cash:,.2f}")
c4.metric("💵 Total Profit", f"₱{st.session_state.total_profit:,.2f}")  # Includes service fees from both cash-ins and cash-outs

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
        fee = compute_service_fee(amount)
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

            # ================= UPDATE BALANCES =================
            if txn_type == "Cash In":
                st.session_state.total_cash += amount  # Add to total cash in
                st.session_state.total_profit += fee    # Increment profit by the service fee for cash in
            elif txn_type == "Cash Out":
                if amount > st.session_state.total_cash:
                    st.error("❌ Insufficient cash to cash out.")
                    st.stop()
                st.session_state.total_cash -= amount  # Deduct amount for cash out
                st.session_state.total_profit += fee     # Increment profit by the service fee for cash out

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
        # Make a multi-select box for multiple deletions
        selected_indices = st.multiselect(
            "Select transactions to delete",
            options=[f"{index} | {row['Customer']} | ₱{row['Amount']:.2f}" for index, row in df.iterrows()]
        )
        
        if st.button("❌ Delete Selected Transactions"):
            if selected_indices:
                for selected in selected_indices:
                    idx = int(selected.split(" | ")[0])  # Extract index for deletion
                    file = df.loc[idx, "Screenshot"]
                    transaction_type = df.loc[idx, "Type"]
                    amount = df.loc[idx, "Amount"]
                    fee = df.loc[idx, "Service Fee"]
                    
                    # Adjust balances based on transaction type when deleting
                    if transaction_type == "Cash In":
                        st.session_state.total_cash -= amount
                        st.session_state.total_profit -= fee  # Decrement profit by the service fee for cash in
                    elif transaction_type == "Cash Out":
                        st.session_state.total_cash += amount
                        st.session_state.total_profit -= fee   # Decrement profit by the service fee for cash out

                    # Remove the associated screenshot
                    path = os.path.join(UPLOAD_FOLDER, file)
                    if os.path.exists(path):
                        os.remove(path)

                    # Drop the transaction from the dataframe
                    df.drop(index=idx, inplace=True)

                df.reset_index(drop=True, inplace=True)
                save_with_images(df)
                st.success("✅ Selected transactions deleted")
                st.session_state.gcash_balance, st.session_state.total_cash, st.session_state.total_profit = recalc_balances(df)  # Recalculate balances
                st.rerun()  # Refresh the page to reflect changes
            else:
                st.warning("Please select at least one transaction to delete.")
        
        # Show transaction history in the app
        st.write(df)

# ================= TAB 3 =================
with tab3:
    st.subheader("🗑 Delete Transaction (Admin Only)")
    if "admin" not in st.session_state:
        st.session_state.admin = False

    if not st.session_state.admin:
        u = st.text_input("Admin Username")
        p = st.text_input("Admin Password", type="password")
        if st.button("🔒 Login"):
            if u == "admin" and p == "adminpass":
                st.session_state.admin = True
                st.success("Logged in")
                st.rerun()
            else:
                st.error("Invalid credentials")
    else:
        st.info("Use the transaction history tab to delete transactions.")
