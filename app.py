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
CAPITAL = 15000

ADMIN_USERNAME = "jepollogcash"
ADMIN_PASSWORD = "jepollogcash"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

st.set_page_config(
    page_title="GCash Cash In / Cash Out",
    page_icon="💙",
    layout="wide"
)

# ================= STYLE =================
st.markdown("""
<style>
.stButton > button {
    background-color: #0057ff;
    color: white;
    border-radius: 8px;
    height: 42px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ================= FUNCTIONS =================
def compute_service_fee(amount):
    return math.ceil(amount / 250) * 5 if amount > 0 else 0

def create_excel():
    df = pd.DataFrame(columns=[
        "Date",
        "Type",
        "Customer",
        "Amount",
        "Service Fee",
        "Screenshot",
        "Remarks"
    ])
    df.to_excel(EXCEL_FILE, index=False)
    return df

def save_with_images(df):
    df.to_excel(EXCEL_FILE, index=False)
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active

    for i, file in enumerate(df["Screenshot"], start=2):
        if isinstance(file, str) and file:  # Ensure file is a string
            path = os.path.join(UPLOAD_FOLDER, file)
            if os.path.exists(path):
                img = XLImage(path)
                img.width = img.height = 70
                ws.add_image(img, f"F{i}")
    wb.save(EXCEL_FILE)

def load_data():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)

        rename_map = {
            "Transaction Type": "Type",
            "Customer Name": "Customer",
            "Reference Screenshot": "Screenshot"
        }

        for old, new in rename_map.items():
            if old in df.columns and new not in df.columns:
                df.rename(columns={old: new}, inplace=True)

        df.to_excel(EXCEL_FILE, index=False)
    else:
        df = create_excel()

    return df

# ================= LOAD DATA =================
df = load_data()

# ================= COMPUTATIONS =================
if not df.empty:
    total_profit = df["Service Fee"].sum()
    cash_in = df[df["Type"] == "Cash In"]["Amount"].sum()
    cash_out = df[df["Type"] == "Cash Out"]["Amount"].sum()
else:
    total_profit = cash_in = cash_out = 0

# Track GCash amount and cash amount separately
gcash_balance = CAPITAL + cash_in - cash_out  # GCash balance after transactions
total_cash = total_profit  # Total cash includes profits

# Store balances in session state for persistence
if "gcash_balance" not in st.session_state:
    st.session_state.gcash_balance = gcash_balance

if "total_cash" not in st.session_state:
    st.session_state.total_cash = total_cash

# ================= HEADER =================
st.title("💙 GCash Cash In / Cash Out System")

c1, c2, c3 = st.columns(3)
c1.metric("💼 Capital", f"₱{CAPITAL:,.2f}")
c2.metric("💰 GCash Balance", f"₱{st.session_state.gcash_balance:,.2f}")
c3.metric("🤑 Total Cash (including profit)", f"₱{st.session_state.total_cash:,.2f}")

if st.session_state.gcash_balance < CAPITAL:
    st.error("⚠ GCash balance is BELOW capital. Add CASH IN.")

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

        screenshot = st.file_uploader(
            "Upload Reference Screenshot",
            type=["jpg", "jpeg", "png"]
        )

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
                st.session_state.total_cash += amount + fee  # Add cash and profit (fee)
            elif txn_type == "Cash Out":
                if amount > st.session_state.gcash_balance:
                    st.error("❌ Insufficient GCash balance.")
                else:
                    st.session_state.gcash_balance -= amount  # Subtract cash from GCash
            
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
            # Check if the file is a valid string (not float or NaN)
            if isinstance(file, str) and file:
                path = os.path.join(UPLOAD_FOLDER, file)
                if os.path.exists(path):  # Ensure the file exists
                    return f'<img src="{path}" width="60">'
            return ''  # Return an empty string for invalid files

        view_df = df.copy()
        view_df["Screenshot"] = view_df["Screenshot"].apply(thumb)

        # Display the DataFrame more clearly
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
            if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
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

                    # Ensure 'file' is a valid string before proceeding
                    if isinstance(file, str) and file:
                        path = os.path.join(UPLOAD_FOLDER, file)

                        # Adjust balances based on transaction type
                        if df.loc[idx, "Type"] == "Cash In":
                            st.session_state.total_cash -= df.loc[idx, "Amount"] + df.loc[idx, "Service Fee"]
                        elif df.loc[idx, "Type"] == "Cash Out":
                            st.session_state.gcash_balance += df.loc[idx, "Amount"]

                        # Delete the file if it exists
                        if os.path.exists(path):
                            os.remove(path)
                        else:
                            st.warning("File not found, but transaction will be removed.")

                        df.drop(index=idx, inplace=True)
                        df.reset_index(drop=True, inplace=True)
                        save_with_images(df)

                        st.success("✅ Transaction deleted")
                        st.rerun()
                    else:
                        st.error("❌ Unable to delete transaction: Invalid screenshot file.")
                else:
                    st.warning("Please confirm deletion first.")
