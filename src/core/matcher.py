from sqlalchemy.orm import Session
from datetime import timedelta, date
import sys
import os

# Ensure import paths work if run directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.db.schema import Invoice, Payment, ReconciliationResult, get_engine, InvoiceStatus

def reconcile_all(db_path='data/project.db'):
    """
    Core reconciliation logic.
    Returns a list of match dictionaries AND saves them to ReconciliationResult table.
    """
    engine = get_engine(db_path)
    session = Session(bind=engine)

    # 1. Fetch Candidates
    # Invoices: Only UNPAID
    unpaid_invoices = session.query(Invoice).filter(Invoice.status == 'UNPAID').all()
    
    # Payments: Only those NOT in ReconciliationResult
    matched_payment_ids = session.query(ReconciliationResult.payment_id).all()
    matched_payment_ids = {id[0] for id in matched_payment_ids} # Set for O(1) lookup
    
    all_payments = session.query(Payment).all() # Filter in python for now or subquery
    unreconciled_payments = [p for p in all_payments if p.id not in matched_payment_ids]

    matches = []
    
    used_payment_ids = set()

    for inv in unpaid_invoices:
        best_match = None
        
        for pay in unreconciled_payments:
            if pay.id in used_payment_ids:
                continue
            
            # Hard Constraint: Currency & Amount must match exactly (for MVP)
            if inv.currency != pay.currency:
                continue
                
            if abs(inv.amount - pay.amount) > 0.01: # Float tolerance
                continue
            
            # Soft Constraint: Date within 5 days
            date_diff = abs((pay.date - inv.date).days)
            if date_diff <= 5:
                # Found a potential match
                if best_match is None or date_diff < best_match['date_diff']:
                    best_match = {
                        'payment': pay,
                        'date_diff': date_diff,
                        'confidence': 1.0 if date_diff == 0 else 0.9
                    }
        
        if best_match:
            pay = best_match['payment']
            used_payment_ids.add(pay.id)
            
            # Create Match Record
            match_record = ReconciliationResult(
                invoice_id=inv.id,
                payment_id=pay.id,
                confidence_score=best_match['confidence'],
                match_date=date.today()
            )
            session.add(match_record)
            
            matches.append({
                'invoice': inv,
                'payment': pay,
                'confidence': best_match['confidence'],
                'reason': f"Amount exact match, Date diff: {best_match['date_diff']} days"
            })

    session.commit() # Save matches to Agent DB
    session.close()
    return matches

def audit_integrity(db_path='data/project.db'):
    """
    Checks for discrepancies:
    1. PAID invoices in CRM that have NO record in ReconciliationResults (Audit Fail).
    """
    engine = get_engine(db_path)
    session = Session(bind=engine)
    
    # Get all PAID invoices
    paid_invoices = session.query(Invoice).filter(Invoice.status == 'PAID').all()
    
    issues = []
    
    # Get all Invoice IDs that have been reconciled
    reconciled_invoice_ids = session.query(ReconciliationResult.invoice_id).all()
    reconciled_invoice_ids = {id[0] for id in reconciled_invoice_ids}
    
    for inv in paid_invoices:
        if inv.id not in reconciled_invoice_ids:
            # ALERT: CRM says Paid, but Agent has no record of it!
            issues.append({
                'type': 'GHOST_PAYMENT',
                'invoice': inv,
                'severity': 'HIGH',
                'message': f"Invoice {inv.invoice_number} is PAID in CRM but has no linked Bank Payment."
            })
            
    session.close()
    return issues

if __name__ == "__main__":
    # Test Matcher
    print("--- Running Matcher ---")
    results = reconcile_all()
    print(f"Found {len(results)} new matches.")
    
    # Test Audit
    print("\n--- Running Audit ---")
    issues = audit_integrity()
    if issues:
        print(f"FOUND {len(issues)} INTEGRITY ISSUES:")
        for i in issues:
            print(f"[!] {i['type']}: {i['message']}")
    else:
        print("Audit Passed: No discrepancies found.")
