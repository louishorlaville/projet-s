import streamlit as st
import pandas as pd
import sys
import os

# Adapt path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.db.schema import get_engine, ReconciliationResult
from src.core.matcher import reconcile_all, audit_integrity
from src.integrations.dolibarr import DolibarrClient
from sqlalchemy.orm import Session

st.set_page_config(page_title="Agentic Reconciliation", layout="wide")

st.title("Agentic Reconciliation Dashboard (Dolibarr Connected)")

# --- Sidebar Controls ---
st.sidebar.header("Actions")
if st.sidebar.button("Run Reconciliation & Audit"):
    with st.spinner("Agent is working..."):
        matches = reconcile_all()
        # issues = audit_integrity() # TODO
    st.sidebar.success(f"Processed! Found {len(matches)} new matches.")

# --- Data Loading ---
engine = get_engine('data/project.db')
session = Session(bind=engine)

def load_data():
    client = DolibarrClient()
    
    # Fetch Invoices
    invoices = client.get_unpaid_invoices()
    if invoices:
        df_invoices = pd.DataFrame(invoices)
        # Select relevant cols
        display_cols = ['ref', 'total_ttc', 'date', 'socid'] 
        # socid is customer ID. We might want to fetch name, but keeping simple for MVP.
        # Filter if columns missing
        available_cols = [c for c in display_cols if c in df_invoices.columns]
        df_invoices = df_invoices[available_cols]
    else:
        df_invoices = pd.DataFrame(columns=['ref', 'total_ttc', 'date'])

    # Fetch Payments
    accounts = client.get_bank_accounts()
    all_lines = []
    for acc in accounts:
        lines = client.get_bank_lines(acc['id'])
        if lines:
            for l in lines:
                l['account_label'] = acc['label']
            all_lines.extend(lines)
            
    if all_lines:
        df_payments = pd.DataFrame(all_lines)
        # display cols: label, amount, datev, num_releve
        display_cols = ['label', 'amount', 'datev', 'account_label']
        available_cols = [c for c in display_cols if c in df_payments.columns]
        df_payments = df_payments[available_cols]
    else:
        df_payments = pd.DataFrame(columns=['label', 'amount', 'datev'])

    # Fetch Agent Results (Local)
    results = pd.read_sql(session.query(ReconciliationResult).statement, session.bind)
    
    return df_invoices, df_payments, results

df_invoices, df_payments, df_results = load_data()

# --- Dashboard Layout ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏢 CRM: Invoices (Dolibarr)")
    st.dataframe(
        df_invoices, 
        use_container_width=False
    )

with col2:
    st.subheader("🏦 ERP: Payments (Dolibarr)")
    st.dataframe(
        df_payments, 
        use_container_width=False
    )

st.divider()

# --- Results Section ---
st.subheader("✅ Reconciliation Results (Agent State)")

if not df_results.empty:
    st.dataframe(df_results, use_container_width=False)
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
