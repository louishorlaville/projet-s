import streamlit as st
import pandas as pd
import sys
import os

# Adapt path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.db.schema import get_engine, Invoice, Payment, ReconciliationResult
from src.core.matcher import reconcile_all, audit_integrity
from sqlalchemy.orm import Session

st.set_page_config(page_title="Agentic Reconciliation", layout="wide")

st.title("Agentic Reconciliation Dashboard")

# --- Sidebar Controls ---
st.sidebar.header("Actions")
if st.sidebar.button("Run Reconciliation & Audit"):
    with st.spinner("Agent is working..."):
        matches = reconcile_all()
        issues = audit_integrity()
    st.sidebar.success(f"Processed! Found {len(matches)} new matches and {len(issues)} issues.")

# --- Data Loading ---
engine = get_engine('data/project.db')
session = Session(bind=engine)

def load_data():
    invoices = pd.read_sql(session.query(Invoice).statement, session.bind)
    payments = pd.read_sql(session.query(Payment).statement, session.bind)
    results = pd.read_sql(session.query(ReconciliationResult).statement, session.bind)
    return invoices, payments, results

df_invoices, df_payments, df_results = load_data()

# --- Dashboard Layout ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏢 CRM: Invoices")
    st.dataframe(
        df_invoices, 
        use_container_width=False,
        column_config={
            "invoice_number": st.column_config.TextColumn(width="medium"),
            "customer_name": st.column_config.TextColumn(width="large"),
            "id": st.column_config.NumberColumn(format="%d", width="small"),
        }
    )

with col2:
    st.subheader("🏦 ERP: Payments")
    st.dataframe(
        df_payments, 
        use_container_width=False,
        column_config={
            "description": st.column_config.TextColumn(width="large"),
            "reference_id": st.column_config.TextColumn(width="medium"),
            "id": st.column_config.NumberColumn(format="%d", width="small"),
        }
    )

st.divider()

# --- Results Section ---
st.subheader("✅ Reconciliation Results (Agent State)")

if not df_results.empty:
    # Join with Invoices and Payments for readability
    # Note: efficient queries would do this in SQL, but for MVP pandas merge is fine
    res_enhanced = df_results.merge(df_invoices, left_on='invoice_id', right_on='id', suffixes=('_res', '_inv'))
    res_enhanced = res_enhanced.merge(df_payments, left_on='payment_id', right_on='id', suffixes=('', '_pay'))
    
    display_cols = ['invoice_number', 'customer_name', 'amount', 'reference_id', 'confidence_score', 'match_date']
    st.dataframe(
        res_enhanced[display_cols], 
        use_container_width=False,
        column_config={
            "customer_name": st.column_config.TextColumn(width="large"),
            "invoice_number": st.column_config.TextColumn(width="medium"),
            "reference_id": st.column_config.TextColumn(width="medium"),
        }
    )
else:
    st.info("No reconciliation results found yet. Click 'Run' in the sidebar.")

# --- Audit Section ---
st.subheader("🚨 Integrity Audit (Discrepancies)")
issues = audit_integrity('data/project.db') # Re-run fresh for display

if issues:
    for issue in issues:
        with st.expander(f"{issue['type']}: {issue['invoice'].invoice_number}", expanded=True):
            st.error(issue['message'])
            st.caption(f"Severity: {issue['severity']}")
else:
    st.success("All systems healthy. No discrepancies found.")

session.close()
