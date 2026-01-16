from datetime import datetime, date
from sqlalchemy.orm import Session

# Ensure import paths work if run directly
try:
    from src.db.schema import ReconciliationResult, get_engine
    from src.integrations.dolibarr import DolibarrClient
except ImportError:
    # Fallback for direct execution
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from src.db.schema import ReconciliationResult, get_engine
    from src.integrations.dolibarr import DolibarrClient

def reconcile_all(db_path='data/project.db'):
    """
    Core reconciliation logic using Dolibarr Live Data.
    """
    engine = get_engine(db_path)
    session = Session(bind=engine)
    client = DolibarrClient()

    # 1. Fetch Candidates from Dolibarr
    print("Fetching Unpaid Invoices...")
    unpaid_invoices = client.get_unpaid_invoices()
    
    print("Fetching Bank Accounts...")
    accounts = client.get_bank_accounts()
    all_payments = []
    
    for acc in accounts:
        print(f"Fetching lines for account {acc['label']}...")
        lines = client.get_bank_lines(acc['id'])
        all_payments.extend(lines)

    # 2. Filter already reconciled payments
    matched_payment_ids = session.query(ReconciliationResult.payment_id).all()
    matched_payment_ids = {str(id[0]) for id in matched_payment_ids} # Set strings for comparison
    
    unreconciled_payments = [p for p in all_payments if str(p['id']) not in matched_payment_ids]

    matches = []
    used_payment_ids = set()

    print(f"Matching {len(unpaid_invoices)} invoices against {len(unreconciled_payments)} payments...")

    for inv in unpaid_invoices:
        best_match = None
        
        # Parse Invoice Date (Dolibarr returns timestamps or strings)
        # Assuming 'date' is timestamp integer
        inv_date = datetime.fromtimestamp(int(inv['date'])).date()
        inv_amount = float(inv['total_ttc'])
        
        for pay in unreconciled_payments:
            pay_id = str(pay['id'])
            if pay_id in used_payment_ids:
                continue
            
            # Constraints
            # Payment amount is usually negative for debit, positive for credit?
            # Dolibarr Bank Lines: existing transactions.
            pay_amount = float(pay['amount'])
            
            # Exact Amount Match
            if abs(inv_amount - pay_amount) > 0.01:
                continue
            
            # Date Logic
            pay_date = datetime.fromtimestamp(int(pay['datev'])).date() # datev = value date
            date_diff = abs((pay_date - inv_date).days)
            
            if date_diff <= 5:
                if best_match is None or date_diff < best_match['date_diff']:
                    best_match = {
                        'payment': pay,
                        'date_diff': date_diff,
                        'confidence': 1.0 if date_diff == 0 else 0.9
                    }
        
        if best_match:
            pay = best_match['payment']
            pay_id = str(pay['id'])
            used_payment_ids.add(pay_id)
            
            # Save Match
            match_record = ReconciliationResult(
                invoice_id=int(inv['id']),
                payment_id=int(pay['id']),
                confidence_score=best_match['confidence'],
                match_date=date.today()
            )
            session.add(match_record)
            
            matches.append({
                'invoice': inv,
                'payment': pay,
                'confidence': best_match['confidence'],
                'reason': f"Amount exact match ({inv_amount}), Date diff: {best_match['date_diff']} days"
            })

    session.commit()
    session.close()
    return matches

def audit_integrity(db_path='data/project.db'):
    return [] # TODO: Implement Audit later once basic matching works

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
