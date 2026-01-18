import streamlit as st
import psycopg2
import pandas as pd
import hashlib
import os
from datetime import date, timedelta
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# ================= CONFIG =================
load_dotenv()
st.set_page_config(page_title="Ganapathi Finance", layout="centered")
APP = "🪔 Ganapathi Finance"

# ================= DB =================
def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ================= SESSION =================
for k, v in {
    "logged_in": False,
    "page": "login",
    "customer_id": None
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def go(p):
    st.session_state.page = p

# ================= PDF =================
def generate_pdf(customer, loan, hist):
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    y = A4[1] - 40

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, "GANAPATHI FINANCE – LOAN STATEMENT")
    y -= 30

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Customer: {customer['name']} ({customer['customer_code']})")
    y -= 14
    pdf.drawString(40, y, f"Loan Amount: ₹{loan['total_amount']}")
    y -= 14
    pdf.drawString(40, y, f"Start: {loan['start_date']}   End: {loan['end_date']}")
    y -= 20

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(40, y, "Date")
    pdf.drawString(130, y, "Due")
    pdf.drawString(190, y, "Paid")
    pdf.drawString(250, y, "Status")
    y -= 12

    pdf.setFont("Helvetica", 10)
    for _, r in hist.iterrows():
        if y < 50:
            pdf.showPage()
            y = A4[1] - 40
        pdf.drawString(40, y, str(r["collection_date"]))
        pdf.drawString(130, y, f"₹{r['amount_due']}")
        pdf.drawString(190, y, f"₹{r['amount_paid']}")
        pdf.drawString(250, y, r["status"])
        y -= 12

    pdf.showPage()
    pdf.save()
    buf.seek(0)
    return buf

# ================= LOGIN =================
if not st.session_state.logged_in:
    st.markdown(f"## {APP}")
    st.markdown("### Daily Finance Management System")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        con = get_conn()
        cur = con.cursor()
        cur.execute("SELECT password_hash FROM users WHERE username=%s", (u,))
        r = cur.fetchone()
        cur.close(); con.close()

        if r and r[0] == hash_password(p):
            st.session_state.logged_in = True
            go("dashboard")
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.stop()

# ================= TOP NAV (BIG BOXES) =================
def top_nav():
    st.markdown("###")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.button("🏠\nDashboard", use_container_width=True, on_click=lambda: go("dashboard"))
    c2.button("👥\nCustomers", use_container_width=True, on_click=lambda: go("customers"))
    c3.button("💰\nDaily\nCollection", use_container_width=True, on_click=lambda: go("collection"))
    c4.button("➕\nNew\nLoan", use_container_width=True, on_click=lambda: go("new_customer"))
    c5.button("📊\nReports", use_container_width=True, on_click=lambda: go("reports"))
    st.divider()

# ================= DASHBOARD =================
if st.session_state.page == "dashboard":
    top_nav()
    st.markdown(f"## {APP} – Dashboard")

    con = get_conn()
    today = date.today()

    k = pd.read_sql("""
        SELECT
        (SELECT COUNT(*) FROM customers) total_customers,
        (SELECT COUNT(*) FROM loans WHERE status='Active') active_loans,
        (SELECT COUNT(*) FROM loans WHERE status='Closed') closed_loans,
        (SELECT COALESCE(SUM(amount_paid),0) FROM daily_collections WHERE collection_date=%s) collected,
        (SELECT COALESCE(SUM(amount_due),0) FROM daily_collections WHERE collection_date=%s) expected
    """, con, params=(today, today)).iloc[0]

    trend = pd.read_sql("""
        SELECT collection_date, SUM(amount_paid) amount
        FROM daily_collections
        GROUP BY collection_date
        ORDER BY collection_date DESC
        LIMIT 20
    """, con)
    con.close()

    st.metric("Total Customers", int(k.total_customers))
    st.metric("Active Loans", int(k.active_loans))
    st.metric("Completed Loans", int(k.closed_loans))
    st.metric("Today Collected", f"₹{int(k.collected)}")
    st.metric("Today Expected", f"₹{int(k.expected)}")

    st.divider()
    st.line_chart(trend.set_index("collection_date"))

# ================= NEW CUSTOMER =================
elif st.session_state.page == "new_customer":
    top_nav()
    st.markdown(f"## {APP} – New Customer")

    code = st.text_input("Customer ID")
    name = st.text_input("Name")
    mobile = st.text_input("Mobile")
    address = st.text_area("Address")

    st.divider()
    total = st.number_input("Loan Amount", min_value=0)
    daily = st.number_input("Daily Amount", min_value=0)
    days = st.number_input("Duration (Days)", value=100, min_value=1)
    loan_date = st.date_input("Loan Date", value=date.today())

    if st.button("Create Customer & Loan", use_container_width=True):
        start = loan_date + timedelta(days=1)
        end = start + timedelta(days=days - 1)

        con = get_conn()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO customers (customer_code,name,mobile1,address)
            VALUES (%s,%s,%s,%s) RETURNING id
        """, (code, name, mobile, address))
        cid = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO loans
            (customer_id,total_amount,amount_given,interest,
             daily_amount,duration_days,loan_date,start_date,end_date,status)
            VALUES (%s,%s,%s,0,%s,%s,%s,%s,%s,'Active')
            RETURNING id
        """, (cid, total, total, daily, days, loan_date, start, end))
        lid = cur.fetchone()[0]

        for i in range(days):
            cur.execute("""
                INSERT INTO daily_collections
                (loan_id,collection_date,amount_due,amount_paid,status)
                VALUES (%s,%s,%s,0,'Pending')
            """, (lid, start + timedelta(days=i), daily))

        con.commit()
        cur.close(); con.close()
        st.success("Customer & Loan Created")
        go("dashboard")
        st.rerun()

# ================= CUSTOMERS (SMART SEARCH) =================
elif st.session_state.page == "customers":
    top_nav()
    st.markdown(f"## {APP} – Customers")

    search = st.text_input("🔍 Search (Name / Customer ID)", placeholder="Type name or ID")

    con = get_conn()
    df = pd.read_sql("""
        SELECT c.id,c.name,c.customer_code,
               l.id loan_id,l.total_amount,l.start_date,l.end_date,l.status
        FROM customers c
        JOIN loans l ON c.id=l.customer_id
        ORDER BY c.id DESC
    """, con)
    con.close()

    if search:
        s = search.lower()
        df = df[
            df["name"].str.lower().str.contains(s)
            | df["customer_code"].str.lower().str.contains(s)
        ]

    for _, r in df.iterrows():
        with st.container(border=True):
            st.write(f"**{r['name']}** ({r['customer_code']})")
            st.write(f"₹{r['total_amount']} | {r['start_date']} → {r['end_date']} | {r['status']}")
            if st.button("Open", key=int(r.loan_id)):
                st.session_state.customer_id = int(r.id)
                go("customer_dashboard")
                st.rerun()

# ================= CUSTOMER DASHBOARD =================
elif st.session_state.page == "customer_dashboard":
    top_nav()
    cid = st.session_state.customer_id

    con = get_conn()
    customer = pd.read_sql("SELECT * FROM customers WHERE id=%s", con, params=(cid,)).iloc[0]
    loans = pd.read_sql("SELECT * FROM loans WHERE customer_id=%s ORDER BY id DESC", con, params=(cid,))
    con.close()

    st.markdown(f"## 👤 {customer['name']} – Loan History")

    for _, loan in loans.iterrows():
        lid = loan.id
        con = get_conn()
        hist = pd.read_sql("""
            SELECT collection_date,amount_due,amount_paid,status
            FROM daily_collections WHERE loan_id=%s
            ORDER BY collection_date
        """, con, params=(lid,))
        con.close()

        paid = hist.amount_paid.sum()
        remaining = loan.total_amount - paid

        with st.container(border=True):
            st.subheader(f"₹{loan.total_amount} | {loan.start_date} → {loan.end_date}")
            st.write(f"Paid ₹{paid} | Remaining ₹{remaining} | Status {loan.status}")

            st.dataframe(hist, height=200, use_container_width=True)

            pdf = generate_pdf(customer, loan, hist)
            st.download_button(
                "📄 Download PDF",
                pdf,
                f"{customer['name']}_loan_{lid}.pdf",
                "application/pdf"
            )

# ================= DAILY COLLECTION (SMART + FAST) =================
elif st.session_state.page == "collection":
    top_nav()
    st.markdown(f"## {APP} – 💰 Daily Collection")

    sel_date = st.date_input("Date", value=date.today())
    search = st.text_input("🔍 Quick Search", placeholder="Search customer name")

    con = get_conn()
    df = pd.read_sql("""
        SELECT dc.id,c.name,l.total_amount,
               dc.amount_due,dc.amount_paid
        FROM daily_collections dc
        JOIN loans l ON dc.loan_id=l.id
        JOIN customers c ON l.customer_id=c.id
        WHERE dc.collection_date=%s AND l.status='Active'
        ORDER BY c.name
    """, con, params=(sel_date,))
    con.close()

    if search:
        df = df[df["name"].str.lower().str.contains(search.lower())]

    expected = int(df.amount_due.sum())
    collected = int(df.amount_paid.sum())
    pending = expected - collected

    k1, k2, k3 = st.columns(3)
    k1.metric("Expected", f"₹{expected}")
    k2.metric("Collected", f"₹{collected}")
    k3.metric("Pending", f"₹{pending}")

    QUICK = [0, 50, 100, 200, 300, 400, 500, 1000]

    for _, r in df.iterrows():
        status_icon = "🟢" if r.amount_paid > 0 else "🔴"
        with st.container(border=True):
            a,b,c,d,e,f = st.columns([3,2,2,2,2,1])
            a.write(f"{status_icon} **{r['name']}**")
            b.write(f"Loan ₹{r['total_amount']}")
            c.write(f"Due ₹{r['amount_due']}")

            quick = d.selectbox("Quick", QUICK, key=f"q{r.id}", label_visibility="collapsed")
            amt = e.number_input("Paid", min_value=0,
                                 value=quick if quick > 0 else r.amount_paid,
                                 key=f"p{r.id}", label_visibility="collapsed")

            if f.button("✔", key=f"s{r.id}"):
                con = get_conn()
                cur = con.cursor()
                cur.execute("""
                    UPDATE daily_collections
                    SET amount_paid=%s,status=%s WHERE id=%s
                """, (amt, "Paid" if amt > 0 else "Missed", r.id))
                con.commit()
                cur.close(); con.close()
                st.rerun()

    st.divider()
    st.bar_chart(pd.DataFrame(
        {"Amount":[expected, collected, pending]},
        index=["Expected","Collected","Pending"]
    ))

# ================= REPORTS =================
elif st.session_state.page == "reports":
    top_nav()
    st.markdown(f"## {APP} – Reports")

    con = get_conn()
    profit = pd.read_sql("SELECT SUM(interest) FROM loans WHERE status='Closed'", con)
    overdue = pd.read_sql("""
        SELECT c.name, COUNT(*) missed_days
        FROM daily_collections d
        JOIN loans l ON d.loan_id=l.id
        JOIN customers c ON l.customer_id=c.id
        WHERE d.amount_paid=0 AND l.status='Active'
        GROUP BY c.name
    """, con)
    con.close()

    st.metric("Total Profit", f"₹{int(profit.iloc[0][0] or 0)}")
    st.dataframe(overdue, use_container_width=True)
