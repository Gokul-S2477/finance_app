# =============================================================================
# GANAPATHI FINANCE – FULL APP (BUG FIXED + STABLE)
# =============================================================================

import os, io, hashlib
from datetime import date, timedelta

import streamlit as st
import psycopg2
import pandas as pd
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# -----------------------------------------------------------------------------
# ENV
# -----------------------------------------------------------------------------
load_dotenv()

# -----------------------------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Ganapathi Finance", layout="wide", initial_sidebar_state="collapsed")
APP_NAME = "🪔 Ganapathi Finance"

# -----------------------------------------------------------------------------
# FORCE WHITE UI
# -----------------------------------------------------------------------------
st.markdown("""
<style>
html, body, [data-testid="stApp"] { background:#ffffff !important; color:#111111 !important; }
h1,h2,h3,h4 { font-family: Segoe UI, system-ui; }
.card { background:#fff; padding:20px; border-radius:18px; box-shadow:0 6px 18px rgba(0,0,0,.08); margin-bottom:18px }
.kpi { text-align:center; padding:18px; border-radius:16px; box-shadow:0 4px 14px rgba(0,0,0,.08) }
.blue{border-left:6px solid #2563eb} .green{border-left:6px solid #16a34a}
.orange{border-left:6px solid #ea580c} .red{border-left:6px solid #dc2626}
.big-btn button{height:90px!important;font-size:20px!important;border-radius:18px!important}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATABASE
# -----------------------------------------------------------------------------
def get_conn():
    try:
        return psycopg2.connect(os.getenv("DATABASE_URL"), sslmode="require", connect_timeout=5)
    except Exception as e:
        st.error("Database connection failed")
        st.code(str(e))
        st.stop()

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

# -----------------------------------------------------------------------------
# PDF
# -----------------------------------------------------------------------------
def loan_pdf(customer, loan, hist):
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    y = A4[1] - 40

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, "GANAPATHI FINANCE – LOAN STATEMENT")
    y -= 30

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Customer: {customer['name']} ({customer['customer_code']})")
    y -= 14
    pdf.drawString(40, y, f"Loan Amount: ₹{loan['total_amount']} | Status: {loan['status']}")
    y -= 20

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(40, y, "Date")
    pdf.drawString(160, y, "Due")
    pdf.drawString(230, y, "Paid")
    pdf.drawString(300, y, "Status")
    y -= 12

    pdf.setFont("Helvetica", 10)
    for _, r in hist.iterrows():
        if y < 60:
            pdf.showPage()
            y = A4[1] - 40
        pdf.drawString(40, y, str(r["collection_date"]))
        pdf.drawString(160, y, f"₹{r['amount_due']}")
        pdf.drawString(230, y, f"₹{r['amount_paid']}")
        pdf.drawString(300, y, r["status"])
        y -= 12

    pdf.save()
    buf.seek(0)
    return buf

# -----------------------------------------------------------------------------
# SESSION
# -----------------------------------------------------------------------------
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("page", "login")
st.session_state.setdefault("customer_id", None)

def go(p): st.session_state.page = p

# =============================================================================
# LOGIN
# =============================================================================
if not st.session_state.logged_in:
    st.markdown(f"# {APP_NAME}")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        con = get_conn(); cur = con.cursor()
        cur.execute("SELECT password_hash FROM users WHERE username=%s", (u,))
        r = cur.fetchone()
        con.close()

        if r and r[0] == hash_password(p):
            st.session_state.logged_in = True
            go("dashboard"); st.rerun()
        else:
            st.error("Invalid login")
    st.stop()

# =============================================================================
# DASHBOARD
# =============================================================================
if st.session_state.page == "dashboard":
    st.markdown(f"# {APP_NAME}")

    con = get_conn()
    today = date.today()
    k = pd.read_sql("""
        SELECT
        (SELECT COUNT(*) FROM customers) customers,
        (SELECT COUNT(*) FROM loans WHERE status='Active') active,
        (SELECT COALESCE(SUM(amount_paid),0) FROM daily_collections WHERE collection_date=%s) collected
    """, con, params=(today,)).iloc[0]
    con.close()

    c1,c2,c3 = st.columns(3)
    c1.markdown(f"<div class='kpi blue'><h4>Customers</h4><h2>{k.customers}</h2></div>",True)
    c2.markdown(f"<div class='kpi orange'><h4>Active Loans</h4><h2>{k.active}</h2></div>",True)
    c3.markdown(f"<div class='kpi green'><h4>Today</h4><h2>₹{k.collected}</h2></div>",True)

    st.divider()
    b1,b2,b3,b4 = st.columns(4)

    with b1:
        st.markdown("<div class='big-btn'>",True)
        if st.button("➕ NEW CUSTOMER",use_container_width=True):
            go("new_customer"); st.rerun()
        st.markdown("</div>",True)

    with b2:
        st.markdown("<div class='big-btn'>", unsafe_allow_html=True)
        if st.button("👥 CUSTOMERS", use_container_width=True):
            go("customers")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


    with b3:
        st.markdown("<div class='big-btn'>",True)
        if st.button("💰 DAILY COLLECTION",use_container_width=True):
            go("collection"); st.rerun()
        st.markdown("</div>",True)

    with b4:
        st.markdown("<div class='big-btn'>",True)
        if st.button("📊 REPORTS",use_container_width=True):
            go("reports"); st.rerun()
        st.markdown("</div>",True)

# =============================================================================
# NEW CUSTOMER
# =============================================================================
elif st.session_state.page == "new_customer":
    st.button("⬅ Back", on_click=lambda: go("dashboard"))
    st.markdown("## ➕ New Customer")

    with st.form("new_customer"):
        code = st.text_input("Customer ID")
        name = st.text_input("Name")
        mobile = st.text_input("Mobile")
        address = st.text_area("Address")

        total = st.number_input("Loan Amount", min_value=0)
        daily = st.number_input("Daily Amount", min_value=1)
        days = st.number_input("Days", min_value=1, value=100)
        loan_date = st.date_input("Loan Date", value=date.today())

        submit = st.form_submit_button("CREATE")

    if submit:
        start = loan_date + timedelta(days=1)
        end = start + timedelta(days=days-1)

        con = get_conn(); cur = con.cursor()
        cur.execute("""
            INSERT INTO customers (customer_code,name,mobile1,address)
            VALUES (%s,%s,%s,%s) RETURNING id
        """,(code,name,mobile,address))
        cid = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO loans (customer_id,total_amount,daily_amount,duration_days,
                               loan_date,start_date,end_date,status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,'Active')
        """,(cid,total,daily,days,loan_date,start,end))

        for i in range(days):
            cur.execute("""
                INSERT INTO daily_collections (loan_id,collection_date,amount_due,amount_paid,status)
                VALUES ((SELECT id FROM loans WHERE customer_id=%s ORDER BY id DESC LIMIT 1),
                        %s,%s,0,'Pending')
            """,(cid,start+timedelta(days=i),daily))

        con.commit(); con.close()
        st.success("Customer created")
        go("dashboard"); st.rerun()

# =============================================================================
# CUSTOMERS PAGE
# =============================================================================
elif st.session_state.page == "customers":

    st.button("⬅ Back", on_click=lambda: go("dashboard"))
    st.markdown("## 👥 Customers")

    search = st.text_input("🔍 Search by Name or Customer ID")

    con = get_conn()
    df = pd.read_sql("""
        SELECT
            c.id,
            c.customer_code,
            c.name,
            c.mobile1,
            COUNT(l.id) AS total_loans
        FROM customers c
        LEFT JOIN loans l ON c.id = l.customer_id
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """, con)
    con.close()

    if search:
        s = search.lower()
        df = df[
            df["name"].str.lower().str.contains(s) |
            df["customer_code"].str.lower().str.contains(s)
        ]

    if df.empty:
        st.info("No customers found")
    else:
        for _, r in df.iterrows():
            st.markdown("<div class='card'>", unsafe_allow_html=True)

            a, b = st.columns([4, 1])
            a.markdown(f"### {r['name']} ({r['customer_code']})")
            a.write(f"📞 {r['mobile1']} | Loans: {r['total_loans']}")

            if b.button("OPEN", key=f"cust_{r['id']}"):
                st.session_state.customer_id = r["id"]
                go("customer_dashboard")
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# CUSTOMER DASHBOARD (FULL PREVIEW + EDIT + DELETE)
# =============================================================================
elif st.session_state.page == "customer_dashboard":

    st.button("⬅ Back", on_click=lambda: go("customers"))

    cid = st.session_state.customer_id
    con = get_conn()

    customer = pd.read_sql(
        "SELECT * FROM customers WHERE id=%s",
        con, params=(cid,)
    ).iloc[0]

    loans = pd.read_sql(
        "SELECT * FROM loans WHERE customer_id=%s ORDER BY id DESC",
        con, params=(cid,)
    )

    # -------------------------------------------------------------------------
    # CUSTOMER PREVIEW
    # -------------------------------------------------------------------------
    st.markdown(f"# 👤 {customer['name']} ({customer['customer_code']})")

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.write(f"📞 **Mobile 1:** {customer['mobile1']}")
    c2.write(f"📞 **Mobile 2:** {customer.get('second_mobile','-') or '-'}")
    c3.write(f"🪪 **Aadhar:** {customer.get('aadhar_number','-') or '-'}")

    c4, c5 = st.columns(2)
    c4.write(f"👥 **Referral:** {customer.get('referral_name','-') or '-'}")
    c5.write(f"🏠 **Address:** {customer['address']}")
    st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # EDIT CUSTOMER DETAILS
    # -------------------------------------------------------------------------
    with st.expander("✏️ Edit Customer Details"):
        with st.form("edit_customer"):
            name = st.text_input("Name", value=customer["name"])
            aadhar = st.text_input("Aadhar", value=customer.get("aadhar_number",""))
            mobile1 = st.text_input("Mobile 1", value=customer["mobile1"])
            mobile2 = st.text_input("Mobile 2", value=customer.get("second_mobile",""))
            referral = st.text_input("Referral", value=customer.get("referral_name",""))
            address = st.text_area("Address", value=customer["address"])

            if st.form_submit_button("SAVE CUSTOMER"):
                cur = con.cursor()
                cur.execute("""
                    UPDATE customers
                    SET name=%s, aadhar_number=%s,
                        mobile1=%s, second_mobile=%s,
                        referral_name=%s, address=%s
                    WHERE id=%s
                """, (name, aadhar, mobile1, mobile2, referral, address, cid))
                con.commit()
                st.success("Customer updated successfully")
                st.rerun()

    # -------------------------------------------------------------------------
    # LOANS SECTION
    # -------------------------------------------------------------------------
    st.markdown("## 💰 Loan History")

    active_loan_exists = False

    for _, loan in loans.iterrows():

        hist = pd.read_sql("""
            SELECT collection_date, amount_due, amount_paid, status
            FROM daily_collections
            WHERE loan_id=%s
            ORDER BY collection_date
        """, con, params=(loan["id"],))

        paid = hist["amount_paid"].sum()
        remaining = loan["total_amount"] - paid
        collection_started = paid > 0

        if loan["status"] == "Active":
            active_loan_exists = True

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader(f"Loan ID: {loan['id']}")

        # ---------------- KPIs ----------------
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total", f"₹{loan['total_amount']}")
        k2.metric("Paid", f"₹{paid}")
        k3.metric("Remaining", f"₹{remaining}")
        k4.metric("Status", loan["status"])
        k5.metric(
            "Collection",
            "Started" if collection_started else "Not Started"
        )

        st.write(
            f"📅 {loan['start_date']} → {loan['end_date']} | "
            f"💵 Daily ₹{loan['daily_amount']} | "
            f"🗓 {loan['duration_days']} days"
        )

        # ---------------- DAILY COLLECTION TABLE ----------------
        st.dataframe(
            hist.style.applymap(
                lambda x: "background-color:#dcfce7" if x == "Paid" else "",
                subset=["status"]
            ),
            use_container_width=True,
            height=260
        )

        st.download_button(
            "📄 Download Loan Statement",
            loan_pdf(customer, loan, hist),
            f"{customer['name']}_loan_{loan['id']}.pdf"
        )

        # ---------------- EDIT LOAN ----------------
        if loan["status"] == "Active" and not collection_started:
            with st.expander("✏️ Edit Loan (Before Collection Starts)"):
                with st.form(f"edit_loan_{loan['id']}"):
                    total = st.number_input("Total Amount", value=loan["total_amount"])
                    interest = st.number_input("Interest", value=loan["interest"])
                    actual = st.number_input("Actual Given", value=loan["actual_given"])
                    daily = st.number_input("Daily Amount", value=loan["daily_amount"])
                    days = st.number_input("Duration (Days)", value=loan["duration_days"])
                    loan_date = st.date_input("Loan Date", value=loan["loan_date"])

                    if st.form_submit_button("UPDATE LOAN"):
                        start = loan_date + timedelta(days=1)
                        end = start + timedelta(days=days - 1)

                        cur = con.cursor()
                        cur.execute("""
                            UPDATE loans
                            SET total_amount=%s, interest=%s, actual_given=%s,
                                daily_amount=%s, duration_days=%s,
                                loan_date=%s, start_date=%s, end_date=%s
                            WHERE id=%s
                        """, (total, interest, actual, daily, days, loan_date, start, end, loan["id"]))

                        cur.execute("DELETE FROM daily_collections WHERE loan_id=%s", (loan["id"],))
                        for i in range(days):
                            cur.execute("""
                                INSERT INTO daily_collections
                                (loan_id, collection_date, amount_due, amount_paid, status)
                                VALUES (%s,%s,%s,0,'Pending')
                            """, (loan["id"], start + timedelta(days=i), daily))

                        con.commit()
                        st.success("Loan updated")
                        st.rerun()

        # ---------------- CLOSE LOAN ----------------
        if loan["status"] == "Active":
            with st.expander("🔒 Close Loan"):
                with st.form(f"close_{loan['id']}"):
                    close_amt = st.number_input("Remaining Amount Collected", value=remaining)
                    close_date = st.date_input("Close Date", value=date.today())

                    if st.form_submit_button("CLOSE LOAN"):
                        cur = con.cursor()
                        cur.execute("UPDATE loans SET status='Closed' WHERE id=%s", (loan["id"],))
                        cur.execute("""
                            UPDATE daily_collections
                            SET amount_paid=%s, status='Paid'
                            WHERE id = (
                                SELECT id FROM daily_collections
                                WHERE loan_id=%s
                                ORDER BY collection_date DESC
                                LIMIT 1
                            )
                        """, (close_amt, loan["id"]))
                        cur.execute("""
                            DELETE FROM daily_collections
                            WHERE loan_id=%s AND collection_date > %s
                        """, (loan["id"], close_date))
                        con.commit()
                        st.success("Loan closed successfully")
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # ADD NEW LOAN
    # -------------------------------------------------------------------------
    if not active_loan_exists:
        st.markdown("<div class='big-btn'>", unsafe_allow_html=True)
        if st.button("➕ ADD NEW LOAN", use_container_width=True):
            go("add_loan")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # DELETE CUSTOMER (PASSWORD PROTECTED)
    # -------------------------------------------------------------------------
    st.divider()
    with st.expander("🗑 DELETE CUSTOMER (DANGER ZONE)"):
        st.warning("This will permanently delete the customer and ALL loan data")

        del_pwd = st.text_input("Delete Password", type="password")
        confirm = st.checkbox("I understand this cannot be undone")

        if st.button("DELETE CUSTOMER PERMANENTLY"):
            if del_pwd != "Grnivas24@":
                st.error("Incorrect password")
            elif not confirm:
                st.error("Please confirm deletion")
            else:
                cur = con.cursor()
                cur.execute("""
                    DELETE FROM daily_collections
                    WHERE loan_id IN (SELECT id FROM loans WHERE customer_id=%s)
                """, (cid,))
                cur.execute("DELETE FROM loans WHERE customer_id=%s", (cid,))
                cur.execute("DELETE FROM customers WHERE id=%s", (cid,))
                con.commit()

                st.success("Customer deleted permanently")
                go("dashboard")
                st.rerun()

    con.close()



# =============================================================================
# ADD NEW LOAN (EXISTING CUSTOMER)
# =============================================================================
elif st.session_state.page == "add_loan":

    st.button("⬅ Back", on_click=lambda: go("customer_dashboard"))

    cid = st.session_state.customer_id
    st.markdown("## ➕ Add New Loan (Existing Customer)")

    con = get_conn()

    active = pd.read_sql("""
        SELECT COUNT(*) cnt
        FROM loans
        WHERE customer_id=%s AND status='Active'
    """, con, params=(cid,)).iloc[0]["cnt"]

    if active > 0:
        st.error("❌ This customer already has an active loan. Close it first.")
        con.close()
        st.stop()

    with st.form("add_new_loan_form"):
        l1, l2, l3 = st.columns(3)
        total_amount = l1.number_input("Total Loan Amount", min_value=0)
        interest = l2.number_input("Interest", min_value=0)
        actual_given = l3.number_input("Actual Given", value=max(total_amount - interest, 0))

        d1, d2, d3 = st.columns(3)
        daily_amount = d1.number_input("Daily Amount", min_value=1)
        duration_days = d2.number_input("Duration (Days)", min_value=1)
        loan_date = d3.date_input("Loan Date", value=date.today())

        submit = st.form_submit_button("CREATE LOAN")

    if submit:
        start_date = loan_date + timedelta(days=1)
        end_date = start_date + timedelta(days=duration_days - 1)

        cur = con.cursor()
        cur.execute("""
            INSERT INTO loans
            (customer_id, total_amount, interest, actual_given,
             daily_amount, duration_days,
             loan_date, start_date, end_date, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Active')
            RETURNING id
        """, (
            cid,
            total_amount, interest, actual_given,
            daily_amount, duration_days,
            loan_date, start_date, end_date
        ))

        loan_id = cur.fetchone()[0]

        for i in range(duration_days):
            cur.execute("""
                INSERT INTO daily_collections
                (loan_id, collection_date, amount_due, amount_paid, status)
                VALUES (%s,%s,%s,0,'Pending')
            """, (
                loan_id,
                start_date + timedelta(days=i),
                daily_amount
            ))

        con.commit()
        con.close()

        st.success("New loan created successfully")
        go("customer_dashboard")
        st.rerun()

# =============================================================================
# DAILY COLLECTION (PLACEHOLDER – CONNECTED)
# =============================================================================
# =============================================================================
# DAILY COLLECTION
# =============================================================================
elif st.session_state.page == "collection":

    st.button("⬅ Back", on_click=lambda: go("dashboard"))
    st.markdown("## 💰 Daily Collection")

    sel_date = st.date_input("📅 Select Date", value=date.today())

    con = get_conn()

    df = pd.read_sql("""
        SELECT
            dc.id,
            c.customer_code,
            c.name,
            dc.amount_due,
            dc.amount_paid,
            dc.status
        FROM daily_collections dc
        JOIN loans l ON dc.loan_id = l.id
        JOIN customers c ON l.customer_id = c.id
        WHERE dc.collection_date = %s
          AND l.status = 'Active'
        ORDER BY c.name
    """, con, params=(sel_date,))

    if df.empty:
        st.info("No collections for this date")
        con.close()
        st.stop()

    # ---------------- KPIs ----------------
    expected = int(df["amount_due"].sum())
    collected = int(df["amount_paid"].sum())
    pending = expected - collected

    k1, k2, k3 = st.columns(3)
    k1.metric("Expected", f"₹{expected}")
    k2.metric("Collected", f"₹{collected}")
    k3.metric("Pending", f"₹{pending}")

    st.divider()

    # ---------------- COLLECTION LIST ----------------
    for _, r in df.iterrows():

        paid = r["amount_paid"] > 0
        bg = "#dcfce7" if paid else "#fee2e2"

        st.markdown(
            f"<div class='card' style='background:{bg}'>",
            unsafe_allow_html=True
        )

        a, b, c, d, e = st.columns([2, 3, 2, 2, 1])

        a.write(f"**{r['customer_code']}**")
        b.write(f"**{r['name']}**")
        c.write(f"Due ₹{r['amount_due']}")

        amt = d.number_input(
            "Paid",
            min_value=0,
            value=int(r["amount_paid"]),
            key=f"amt_{r['id']}",
            label_visibility="collapsed"
        )

        if e.button("✔", key=f"save_{r['id']}"):
            cur = con.cursor()
            cur.execute("""
                UPDATE daily_collections
                SET amount_paid=%s,
                    status=%s
                WHERE id=%s
            """, (
                amt,
                "Paid" if amt > 0 else "Pending",
                r["id"]
            ))
            con.commit()
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    con.close()

# =============================================================================
# REPORTS (PLACEHOLDER – CONNECTED)
# =============================================================================
# =============================================================================
# REPORTS
# =============================================================================
elif st.session_state.page == "reports":

    st.button("⬅ Back", on_click=lambda: go("dashboard"))
    st.markdown("## 📊 Reports")

    # -------------------------------------------------------------------------
    # FILTERS
    # -------------------------------------------------------------------------
    mode = st.radio("Select Report Type", ["Single Date", "Date Range"], horizontal=True)

    if mode == "Single Date":
        from_date = st.date_input("Select Date", value=date.today())
        to_date = from_date
    else:
        c1, c2 = st.columns(2)
        from_date = c1.date_input("From Date", value=date.today() - timedelta(days=7))
        to_date = c2.date_input("To Date", value=date.today())

    con = get_conn()

    # -------------------------------------------------------------------------
    # BASE DATA
    # -------------------------------------------------------------------------
    df = pd.read_sql("""
        SELECT
            dc.collection_date,
            c.customer_code,
            c.name,
            dc.amount_due,
            dc.amount_paid,
            dc.status
        FROM daily_collections dc
        JOIN loans l ON dc.loan_id = l.id
        JOIN customers c ON l.customer_id = c.id
        WHERE dc.collection_date BETWEEN %s AND %s
    """, con, params=(from_date, to_date))

    if df.empty:
        st.warning("No data found for selected period")
        con.close()
        st.stop()

    # -------------------------------------------------------------------------
    # KPIs
    # -------------------------------------------------------------------------
    total_due = int(df["amount_due"].sum())
    total_paid = int(df["amount_paid"].sum())
    total_pending = total_due - total_paid
    customers_paid = df[df["amount_paid"] > 0]["customer_code"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Due", f"₹{total_due}")
    k2.metric("Total Collected", f"₹{total_paid}")
    k3.metric("Total Pending", f"₹{total_pending}")
    k4.metric("Customers Paid", customers_paid)

    st.divider()

    # -------------------------------------------------------------------------
    # CUSTOMER-WISE SUMMARY
    # -------------------------------------------------------------------------
    st.markdown("### 👥 Customer-wise Collection")

    cust_summary = (
        df.groupby(["customer_code", "name"], as_index=False)
        .agg({
            "amount_due": "sum",
            "amount_paid": "sum"
        })
    )
    cust_summary["pending"] = cust_summary["amount_due"] - cust_summary["amount_paid"]

    st.dataframe(cust_summary, use_container_width=True)

    # -------------------------------------------------------------------------
    # DATE-WISE SUMMARY
    # -------------------------------------------------------------------------
    st.markdown("### 📅 Date-wise Collection")

    date_summary = (
        df.groupby("collection_date", as_index=False)
        .agg({
            "amount_due": "sum",
            "amount_paid": "sum"
        })
    )
    date_summary["pending"] = date_summary["amount_due"] - date_summary["amount_paid"]

    st.dataframe(date_summary, use_container_width=True)

    # -------------------------------------------------------------------------
    # PENDING CUSTOMERS
    # -------------------------------------------------------------------------
    st.markdown("### ⏳ Pending Customers")

    pending_df = df[df["amount_paid"] == 0][
        ["collection_date", "customer_code", "name", "amount_due"]
    ]

    if pending_df.empty:
        st.success("No pending customers 🎉")
    else:
        st.dataframe(pending_df, use_container_width=True)

    con.close()
