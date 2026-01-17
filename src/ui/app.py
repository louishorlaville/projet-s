import streamlit as st
import pandas as pd
import sys
import os

# Adapt path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.db.schema import get_engine, ReconciliationResult
from src.core.agentic_matcher import AgenticMatcher
from src.core.audit import audit_reconciliation
from src.integrations.dolibarr import DolibarrClient
from sqlalchemy.orm import Session
from datetime import date

st.set_page_config(page_title="Agentic Reconciliation", layout="wide")

st.title("Agentic Reconciliation Dashboard (Dolibarr Connected)")

# --- Sidebar Controls ---
st.sidebar.header("Actions")

if st.sidebar.button("🤖 Run AI Reconciliation"):
    with st.spinner("AI Agent is analyzing data..."):
        # AI Flow - Give AI ALL data, let it decide
        client = DolibarrClient()
        
        # Fetch ALL invoices (not just unpaid)
        invoices = client.get_all_invoices()
        
        # Get all payments
        accounts = client.get_bank_accounts()
        payments = []
        for acc in accounts:
            payments.extend(client.get_bank_lines(acc['id']))
        
        # Run Agent
        agent = AgenticMatcher()
        ai_matches = agent.smart_reconcile(invoices, payments)
        
        # Save AI results to reconciliation_results table
        if ai_matches:
            engine = get_engine('data/project.db')
            ai_session = Session(bind=engine)
            
            for match in ai_matches:
                # Check if already exists
                exists = ai_session.query(ReconciliationResult).filter_by(
                    invoice_id=int(match['invoice_id']),
                    payment_id=int(match['payment_id'])
                ).first()
                
                if not exists:
                    record = ReconciliationResult(
                        invoice_id=int(match['invoice_id']),
                        payment_id=int(match['payment_id']),
                        confidence_score=float(match.get('confidence', 0.95)),
                        match_date=date.today()
                    )
                    ai_session.add(record)
            
            ai_session.commit()
            ai_session.close()
            st.sidebar.success(f"✅ AI Found & Saved {len(ai_matches)} matches!")
        else:
            st.sidebar.warning("⚠️ AI found no matches.")

# --- Data Loading ---
engine = get_engine('data/project.db')
session = Session(bind=engine)

def load_data():
    client = DolibarrClient()
    
    # Fetch Invoices
    invoices = client.get_all_invoices()
    if invoices:
        df_invoices = pd.DataFrame(invoices)
        
        # Convert timestamp to readable date
        if 'date' in df_invoices.columns:
            df_invoices['date'] = pd.to_datetime(df_invoices['date'].astype(int), unit='s').dt.strftime('%Y-%m-%d')
        
        # Map paye field to readable Status
        if 'paye' in df_invoices.columns:
            df_invoices['Status'] = df_invoices['paye'].map({
                '0': 'Unpaid',
                '1': 'Paid',
                0: 'Unpaid',
                1: 'Paid'
            })

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
        
        # Convert timestamp to readable date
        if 'datev' in df_payments.columns:
            df_payments['datev'] = pd.to_datetime(df_payments['datev'].astype(int), unit='s').dt.strftime('%Y-%m-%d')
    else:
        df_payments = pd.DataFrame(columns=['label', 'amount', 'datev'])

    # Fetch Agent Results (Local)
    results = pd.read_sql(session.query(ReconciliationResult).statement, session.bind)
    
    # Enrich Results with Human Readable Info
    if not results.empty:
        # We need to map invoice_id -> ref, total_ttc
        if not df_invoices.empty and 'id' in df_invoices.columns:
            # Ensure ID is int for merge
            df_invoices['id'] = df_invoices['id'].astype(str)
            results['invoice_id'] = results['invoice_id'].astype(str)
            # Create mapping
            inv_map = df_invoices.set_index('id')[['ref', 'total_ttc']]
            # Map
            results['Invoice Ref'] = results['invoice_id'].map(inv_map['ref'])
            results['Invoice Amount'] = results['invoice_id'].map(inv_map['total_ttc'])
        
        # We need to map payment_id -> amount only (not label)
        if not df_payments.empty and 'id' in df_payments.columns:
             df_payments['id'] = df_payments['id'].astype(str)
             results['payment_id'] = results['payment_id'].astype(str)
             pay_map = df_payments.set_index('id')['amount']
             results['Payment Amount'] = results['payment_id'].map(pay_map)
             # Rename payment_id column for display
             results['Payment ID'] = results['payment_id']

        # Reorder columns for readability
        cols = ['id', 'Invoice Ref', 'Invoice Amount', 'Payment ID', 'Payment Amount', 'confidence_score', 'match_date']
        # Filter strictly existing cols
        final_cols = [c for c in cols if c in results.columns]
        results = results[final_cols]
    
    # NOW filter invoices/payments for display (after mapping is done)
    if not df_invoices.empty:
        display_cols = ['id', 'ref', 'total_ttc', 'date', 'socid', 'Status']
        available_cols = [c for c in display_cols if c in df_invoices.columns]
        df_invoices = df_invoices[available_cols]
    
    if not df_payments.empty:
        display_cols = ['id', 'label', 'amount', 'datev', 'account_label']
        available_cols = [c for c in display_cols if c in df_payments.columns]
        df_payments = df_payments[available_cols]

    return df_invoices, df_payments, results

df_invoices, df_payments, df_results = load_data()

# --- Dashboard Layout ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏢 CRM: Invoices (Dolibarr)")
    st.dataframe(
        df_invoices, 
        use_container_width=True
    )

with col2:
    st.subheader("🏦 ERP: Payments (Dolibarr)")
    st.dataframe(
        df_payments, 
        use_container_width=True
    )

st.divider()

# --- Results Section ---
st.subheader("✅ Reconciliation Results (Agent State)")

if not df_results.empty:
    st.dataframe(df_results, use_container_width=True)
else:
    st.info("No reconciliation results found yet. Click '🤖 Run AI Reconciliation' in the sidebar.")

# --- Audit Section ---
st.divider()
st.subheader("🚨 Integrity Audit")

issues = audit_reconciliation('data/project.db')

if issues:
    # Group by severity
    high_issues = [i for i in issues if i['severity'] == 'HIGH']
    medium_issues = [i for i in issues if i['severity'] == 'MEDIUM']
    
    if high_issues:
        st.error(f"⚠️ {len(high_issues)} HIGH severity issue(s) detected!")
        for issue in high_issues:
            with st.expander(f"🔴 {issue['type']}: {issue['entity_ref']}", expanded=True):
                st.error(issue['message'])
    
    if medium_issues:
        st.warning(f"⚠️ {len(medium_issues)} MEDIUM severity issue(s) detected!")
        for issue in medium_issues:
            with st.expander(f"🟡 {issue['type']}: {issue['entity_ref']}"):
                st.warning(issue['message'])
else:
    st.success("✅ All systems healthy. No discrepancies found.")

session.close()
