"""
Audit functions for detecting reconciliation anomalies.
"""
from sqlalchemy.orm import Session
from src.db.schema import get_engine, ReconciliationResult
from src.integrations.dolibarr import DolibarrClient

def audit_reconciliation(db_path='data/project.db'):
    """
    Audit reconciliation results to detect anomalies:
    - Paid invoices with no reconciliation record (Ghost Payments)
    - Unpaid invoices with no matching payment (Outstanding)
    - Orphan bank transactions (Unmatched Payments)
    """
    engine = get_engine(db_path)
    session = Session(bind=engine)
    client = DolibarrClient()
    
    issues = []
    
    # Get all reconciliation records
    reconciled = session.query(ReconciliationResult).all()
    reconciled_invoice_ids = {str(r.invoice_id) for r in reconciled}
    reconciled_payment_ids = {str(r.payment_id) for r in reconciled}
    
    # Get all invoices and payments from Dolibarr
    all_invoices = client.get_all_invoices()
    
    accounts = client.get_bank_accounts()
    all_payments = []
    for acc in accounts:
        all_payments.extend(client.get_bank_lines(acc['id']))
    
    # 1. Check for PAID invoices without reconciliation record
    for inv in all_invoices:
        if inv.get('paye') == '1' and str(inv['id']) not in reconciled_invoice_ids:
            issues.append({
                'type': 'GHOST_PAYMENT',
                'severity': 'HIGH',
                'entity_type': 'Invoice',
                'entity_id': inv['id'],
                'entity_ref': inv.get('ref', 'N/A'),
                'message': f"Invoice {inv.get('ref')} is marked as PAID in Dolibarr but has no reconciliation record in the system."
            })
    
    # 2. Check for UNPAID invoices (potential outstanding)
    for inv in all_invoices:
        if inv.get('paye') == '0' and str(inv['id']) not in reconciled_invoice_ids:
            issues.append({
                'type': 'OUTSTANDING',
                'severity': 'MEDIUM',
                'entity_type': 'Invoice',
                'entity_id': inv['id'],
                'entity_ref': inv.get('ref', 'N/A'),
                'message': f"Invoice {inv.get('ref')} is unpaid and unmatched. Amount: ${inv.get('total_ttc')}."
            })
    
    # 3. Check for orphan payments (bank transactions with no match)
    for pay in all_payments:
        # Skip initial balance lines
        if pay.get('label') == '(InitialBankBalance)':
            continue
        
        if str(pay['id']) not in reconciled_payment_ids:
            issues.append({
                'type': 'ORPHAN_PAYMENT',
                'severity': 'MEDIUM',
                'entity_type': 'Payment',
                'entity_id': pay['id'],
                'entity_ref': pay.get('label', 'N/A'),
                'message': f"Bank transaction '{pay.get('label')}' (${pay.get('amount')}) has no matching invoice."
            })
    
    session.close()
    return issues
