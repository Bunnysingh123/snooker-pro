import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3

# Data ko save karne ke liye
conn = sqlite3.connect('snooker_data.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS inventory (item TEXT PRIMARY KEY, stock INTEGER, buy_price REAL, sell_price REAL)')
c.execute('CREATE TABLE IF NOT EXISTS customers (name TEXT PRIMARY KEY, credit REAL DEFAULT 0)')
c.execute('CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, customer TEXT, table_no TEXT, game_amt REAL, snack_amt REAL, snack_profit REAL, total REAL, paid REAL, credit REAL, date DATE, time TEXT)')
conn.commit()

st.set_page_config(page_title="Snooker Manager", layout="wide")
st.title("🎱 Snooker Club Pro Manager")

if 'live' not in st.session_state: st.session_state.live = {}

menu = ["🎮 Live Tables", "📦 Inventory", "📊 Daily Report", "💳 Udhaar Records"]
choice = st.sidebar.selectbox("Kahan Jana Hai?", menu)

if choice == "🎮 Live Tables":
    st.header("Tables Status")
    with st.expander("▶️ Nayi Game Start Karein", expanded=True):
        t_no = st.selectbox("Table No.", [f"Table {i}" for i in range(1, 8)])
        durn = st.number_input("Time (Minutes)", min_value=1, value=30)
        if st.button("Start Now"):
            if t_no not in st.session_state.live:
                st.session_state.live[t_no] = {"cust": "Guest", "start": datetime.now(), "limit": durn, "items": []}
                st.rerun()

    cols = st.columns(2)
    for i, (t_id, data) in enumerate(list(st.session_state.live.items())):
        with cols[i % 2]:
            st.info(f"📍 {t_id}")
            st.session_state.live[t_id]["cust"] = st.text_input(f"Customer Name", value=data["cust"], key=f"n_{t_id}")
            elapsed = (datetime.now() - data["start"]).total_seconds() / 60
            if elapsed >= data["limit"]:
                st.error(f"TIME UP! {int(elapsed)} min")
                st.toast(f"{t_id} Time Finish!")
            else: st.success(f"Running: {int(elapsed)} / {data['limit']} min")
            
            c.execute("SELECT item FROM inventory WHERE stock > 0")
            snacks = [r[0] for r in c.fetchall()]
            item = st.selectbox("Saman Add Karein", ["--Select--"] + snacks, key=f"s_{t_id}")
            if st.button(f"Add Saman", key=f"b_{t_id}"):
                if item != "--Select--": 
                    st.session_state.live[t_id]["items"].append(item)
                    st.toast(f"{item} Added")

            if st.button(f"🧾 Final Bill {t_id}", key=f"bill_{t_id}"):
                st.session_state.checkout = st.session_state.live.pop(t_id)
                st.session_state.checkout['t_no'] = t_id
                st.rerun()

    if 'checkout' in st.session_state:
        st.divider()
        b = st.session_state.checkout
        st.write(f"### Checkout: {b['cust']}")
        g_amt = st.number_input("Game Price (₹)", value=100)
        s_total = 0
        s_profit = 0
        for it in b['items']:
            c.execute("SELECT buy_price, sell_price FROM inventory WHERE item=?", (it,))
            res = c.fetchone()
            if res:
                s_total += res[1]
                s_profit += (res[1]-res[0])
        total = g_amt + s_total
        st.write(f"Saman: {', '.join(b['items'])} (₹{s_total})")
        st.write(f"#### Total: ₹{total}")
        paid = st.number_input("Paid Amount (₹)", value=total)
        if st.button("Confirm Payment"):
            now = datetime.now()
            for it in b['items']: c.execute("UPDATE inventory SET stock = stock - 1 WHERE item=?", (it,))
            c.execute("INSERT OR IGNORE INTO customers (name) VALUES (?)", (b['cust'],))
            c.execute("INSERT INTO sales (customer, table_no, game_amt, snack_amt, snack_profit, total, paid, credit, date, time) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (b['cust'], b['t_no'], g_amt, s_total, s_profit, total, paid, total-paid, now.date(), now.strftime("%H:%M")))
            c.execute("UPDATE customers SET credit = credit + ? WHERE name=?", (total-paid, b['cust']))
            conn.commit()
            del st.session_state.checkout
            st.success("Sale Saved!")
            st.rerun()

elif choice == "📦 Inventory":
    st.header("Stock Management")
    with st.expander("Add Saman / Update Stock"):
        n = st.text_input("Item Name")
        bp = st.number_input("Kharidi Rate (Buying Price)")
        sp = st.number_input("Bechne ka Rate (Selling Price)")
        qty = st.number_input("Quantity", min_value=1)
        if st.button("Stock Save"):
            c.execute("INSERT OR REPLACE INTO inventory VALUES (?,?,?,?)", (n, qty, bp, sp))
            conn.commit()
            st.success("Inventory Updated!")
    st.table(pd.read_sql("SELECT * FROM inventory", conn))

elif choice == "📊 Daily Report":
    st.header("Aaj ka Hisaab")
    d = st.date_input("Date Select", datetime.now().date())
    df = pd.read_sql("SELECT * FROM sales WHERE date = ?", conn, params=(d,))
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Sale", f"₹{df['total'].sum()}")
        c2.metric("Saman Profit", f"₹{df['snack_profit'].sum()}")
        c3.metric("Pending Udhaar", f"₹{df['credit'].sum()}")
        st.dataframe(df)
    else: st.info("No records for this date.")

elif choice == "💳 Udhaar Records":
    st.header("Customer Udhaar")
    u_df = pd.read_sql("SELECT name, credit FROM customers WHERE credit > 0", conn)
    st.table(u_df)
    if not u_df.empty:
        cust = st.selectbox("Select Customer to Clear Udhaar", u_df['name'])
        amt = st.number_input("Paying Back Amount (₹)")
        if st.button("Update Payment"):
            c.execute("UPDATE customers SET credit = credit - ? WHERE name=?", (amt, cust))
            conn.commit()
            st.rerun()
import streamlit as st
import pandas as pd
from datetime import datetime
import time

# --- APP CONFIG ---
st.set_page_config(page_title="Snooker Pro", layout="wide")
st.title("🎱 Snooker Club Manager (Permanent Save)")

# Session State for Timer
if 'sessions' not in st.session_state:
    st.session_state.sessions = {}

# --- STEP 1: START GAME (Manual Table Name) ---
st.header("1. Start Game")
c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    t_name = st.text_input("Table ka Name Likhen", placeholder="e.g. Table A, VIP...")
with c2:
    t_mins = st.number_input("Game ka Time (Minutes)", min_value=1, value=30)
with c3:
    st.write(" ")
    if st.button("▶️ Start Timer"):
        if t_name:
            st.session_state.sessions[t_name] = {
                "start": datetime.now(),
                "limit": t_mins
            }
            st.rerun()
        else:
            st.error("Table Name Likhen!")

st.divider()

# --- STEP 2: LIVE TABLES & STOP OPTION ---
st.header("2. Live Tables")
if st.session_state.sessions:
    cols = st.columns(3)
    for i, (name, data) in enumerate(list(st.session_state.sessions.items())):
        with cols[i % 3]:
            st.subheader(f"📍 {name}")
            elapsed = (datetime.now() - data["start"]).total_seconds() / 60
            st.write(f"Time: {int(elapsed)} / {data['limit']} min")
            
            if st.button(f"🛑 Stop {name}", key=f"stop_{name}"):
                st.session_state.billing_now = {
                    "table": name,
                    "mins": data['limit'],
                    "elapsed": int(elapsed)
                }
                del st.session_state.sessions[name]
                st.rerun()
else:
    st.info("Abhi koi table nahi chal rahi.")

# --- STEP 3: BILLING FORM (Jo aapne maanga tha) ---
if 'billing_now' in st.session_state:
    st.divider()
    st.header("3. Checkout & Manual Bill")
    b = st.session_state.billing_now
    
    with st.form("bill_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Table:** {b['table']} | **Set Time:** {b['mins']} min")
            cust = st.text_input("Customer Name (Zaroori)")
            g_amt = st.number_input("Game Amount (Manual)", min_value=0, value=100)
        
        with col2:
            paid = st.number_input("Kitne Paise Aaye? (Paid)", min_value=0, value=0)
            # Yahan hum snacks ko manual add kar sakte hain ya option rakh sakte hain
            s_amt = st.number_input("Saman ka Paisa (Snacks)", min_value=0, value=0)
        
        total = g_amt + s_amt
        credit = total - paid
        st.markdown(f"### Total: ₹{total} | Udhaar: ₹{credit}")
        
        if st.form_submit_button("✅ Save Record Permanently"):
            if cust:
                # DATA STRUCTURE
                new_data = {
                    "Date": [datetime.now().strftime("%Y-%m-%d")],
                    "Time": [datetime.now().strftime("%H:%M")],
                    "Table_Name": [b['table']],
                    "Minutes": [b['mins']],
                    "Customer": [cust],
                    "Game_Amt": [g_amt],
                    "Snack_Amt": [s_amt],
                    "Total": [total],
                    "Paid": [paid],
                    "Credit": [credit]
                }
                
                # IMPORTANT: Yahan hum data ko CSV mein save kar rahe hain backup ke liye
                # GitHub pe hamesha ke liye save karne ke liye Google Sheets connect karni hogi.
                # Abhi ke liye ye aapke session mein rahega jab tak app live hai.
                
                df = pd.DataFrame(new_data)
                st.write("Record Ready to Save!")
                st.dataframe(df)
                
                # Download button as backup (Data delete na ho isliye)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("💾 Download/Save Record", csv, "bill.csv", "text/csv")
                
                del st.session_state.billing_now
                st.success("Bill generate ho gaya! Upar download button se save karein.")
            else:
                st.error("Customer ka naam likhna zaroori hai!")
