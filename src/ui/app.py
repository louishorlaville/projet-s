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

# Page configuration
st.set_page_config(
    page_title="Financial Reconciliation System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional appearance
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 600;
\        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f9fafb;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e5e7eb;
    }
    .section-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #374150;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #e5e7eb;
        padding-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">Financial Reconciliation System</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Automated invoice-to-payment matching with intelligent analysis</div>', unsafe_allow_html=True)

# Sidebar Controls
with st.sidebar:
    st.header("Reconciliation Controls")
    st.markdown("---")
    
    if st.button("Run Reconciliation", type="primary", use_container_width=True):
        with st.spinner("Processing reconciliation..."):
            # AI Flow
            client = DolibarrClient()
            
            # Fetch ALL invoices
            invoices = client.get_all_invoices()
            
            # Get all payments
            accounts = client.get_bank_accounts()
            payments = []
            for acc in accounts:
                payments.extend(client.get_bank_lines(acc['id']))
            
            # Run Agent
            agent = AgenticMatcher()
            ai_matches = agent.smart_reconcile(invoices, payments)
            
            # Save results
            if ai_matches:
                engine = get_engine('data/project.db')
                ai_session = Session(bind=engine)
                
                for match in ai_matches:
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
                st.success(f"Successfully processed {len(ai_matches)} matches")
            else:
                st.warning("No new matches identified")
    
    st.markdown("---")
    st.caption("Connected to Dolibarr ERP")

# Data Loading
engine = get_engine('data/project.db')
session = Session(bind=engine)

def load_data():
    client = DolibarrClient()
    
    # Fetch Invoices
    invoices = client.get_all_invoices()
    thirdparties = client.get_thirdparties()
    
    # Create mapping for thirdparties
    tp_map = {str(tp['id']): tp['name'] for tp in thirdparties} if thirdparties else {}

    if invoices:
        df_invoices = pd.DataFrame(invoices)
        
        # Convert timestamp to readable date
        if 'date' in df_invoices.columns:
            df_invoices['date'] = pd.to_datetime(df_invoices['date'].astype(int), unit='s').dt.strftime('%Y-%m-%d')
        
        # Map socid to Customer Name
        if 'socid' in df_invoices.columns:
            df_invoices['Customer'] = df_invoices['socid'].astype(str).map(tp_map).fillna(df_invoices['socid'])

        # Map paye field to readable Status
        if 'paye' in df_invoices.columns:
            df_invoices['Status'] = df_invoices['paye'].map({
                '0': 'Outstanding',
                '1': 'Paid',
                0: 'Outstanding',
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

    # Fetch Agent Results
    results = pd.read_sql(session.query(ReconciliationResult).statement, session.bind)
    
    # Enrich Results
    if not results.empty:
        if not df_invoices.empty and 'id' in df_invoices.columns:
            df_invoices['id'] = df_invoices['id'].astype(str)
            results['invoice_id'] = results['invoice_id'].astype(str)
            inv_map = df_invoices.set_index('id')[['ref', 'total_ttc']]
            results['Invoice Ref'] = results['invoice_id'].map(inv_map['ref'])
            results['Invoice Amount'] = results['invoice_id'].map(inv_map['total_ttc'])
        
        if not df_payments.empty and 'id' in df_payments.columns:
             df_payments['id'] = df_payments['id'].astype(str)
             results['payment_id'] = results['payment_id'].astype(str)
             pay_map = df_payments.set_index('id')['amount']
             results['Payment Amount'] = results['payment_id'].map(pay_map)
             results['Payment ID'] = results['payment_id']

        cols = ['id', 'Invoice Ref', 'Invoice Amount', 'Payment ID', 'Payment Amount', 'confidence_score', 'match_date']
        final_cols = [c for c in cols if c in results.columns]
        results = results[final_cols]
    
    # Filter for display
    if not df_invoices.empty:
        display_cols = ['id', 'Customer', 'total_ttc', 'date', 'Status']
        available_cols = [c for c in display_cols if c in df_invoices.columns]
        df_invoices = df_invoices[available_cols]
    
    if not df_payments.empty:
        display_cols = ['id', 'label', 'amount', 'datev', 'account_label']
        available_cols = [c for c in display_cols if c in df_payments.columns]
        df_payments = df_payments[available_cols]

    return df_invoices, df_payments, results

df_invoices, df_payments, df_results = load_data()

# Dashboard Layout
st.markdown('<div class="section-title">Source Data</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Accounts Receivable")
    st.caption("Customer invoices from CRM system")
    st.dataframe(
        df_invoices, 
        use_container_width=True,
        hide_index=True
    )

with col2:
    st.subheader("Bank Transactions")
    st.caption("Payment entries from ERP system")
    st.dataframe(
        df_payments, 
        use_container_width=True,
        hide_index=True
    )

# Results Section
st.markdown('<div class="section-title">Reconciliation Results</div>', unsafe_allow_html=True)

if not df_results.empty:
    # Rename confidence_score to Confidence
    if 'confidence_score' in df_results.columns:
        df_results = df_results.rename(columns={'confidence_score': 'Confidence', 'match_date': 'Date Reconciled'})
    
    st.dataframe(df_results, use_container_width=True, hide_index=True)
    st.caption(f"Total matches: {len(df_results)}")
else:
    st.info("No reconciliation records found. Run the reconciliation process to generate matches.")

# Audit Section
st.markdown('<div class="section-title">Discrepancy Analysis</div>', unsafe_allow_html=True)

issues = audit_reconciliation('data/project.db')

if issues:
    # Group by severity
    high_issues = [i for i in issues if i['severity'] == 'HIGH']
    medium_issues = [i for i in issues if i['severity'] == 'MEDIUM']
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Issues", len(issues))
    with col2:
        st.metric("High Severity", len(high_issues), delta=None if len(high_issues) == 0 else f"-{len(high_issues)}", delta_color="inverse")
    with col3:
        st.metric("Medium Severity", len(medium_issues))
    
    st.markdown("---")
    
    if high_issues:
        st.error(f"**Critical Issues Detected ({len(high_issues)})**")
        for issue in high_issues:
            with st.expander(f"{issue['type']}: {issue['entity_ref']}", expanded=True):
                st.markdown(f"**Type:** {issue['entity_type']}")
                st.markdown(f"**Reference:** {issue['entity_ref']}")
                st.markdown(f"**Issue:** {issue['message']}")
    
    if medium_issues:
        st.warning(f"**Review Required ({len(medium_issues)})**")
        for issue in medium_issues:
            with st.expander(f"{issue['type']}: {issue['entity_ref']}"):
                st.markdown(f"**Type:** {issue['entity_type']}")
                st.markdown(f"**Reference:** {issue['entity_ref']}")
                st.markdown(f"**Details:** {issue['message']}")
else:
    st.success("No discrepancies detected. All transactions are properly reconciled.")

session.close()
