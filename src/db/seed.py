import sys
import os
from datetime import date, timedelta
from sqlalchemy.orm import sessionmaker

# Ensure we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.db.schema import Invoice, Payment, ReconciliationResult, get_engine, init_db

def seed_data():
    # Make sure data directory exists
    os.makedirs('data', exist_ok=True)
    
    engine = get_engine('data/project.db')
    init_db(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()

    # Clear existing data
    session.query(ReconciliationResult).delete()
    session.query(Invoice).delete()
    session.query(Payment).delete()

    # --- CRM: Invoices ---
    invoices = [
        # Set 1: Perfect matches
        Invoice(invoice_number="INV-001", date=date(2025, 1, 10), amount=1200.00, customer_name="TechCorp", status="UNPAID"),
        Invoice(invoice_number="INV-002", date=date(2025, 1, 12), amount=450.50, customer_name="DesignStudio", status="UNPAID"),
        
        # Set 2: Date mismatch (Paid 2 days later)
        Invoice(invoice_number="INV-003", date=date(2025, 1, 15), amount=3000.00, customer_name="BigRetail", status="UNPAID"),
        
        # Set 3: Unpaid (No matching payment)
        Invoice(invoice_number="INV-004", date=date(2025, 1, 20), amount=99.99, customer_name="SmallBiz", status="UNPAID"),
        
        # Set 4: Already Paid (Should be ignored by reconciler ideally, but good for data)
        Invoice(invoice_number="INV-005", date=date(2025, 1, 5), amount=500.00, customer_name="LoyalClient", status="PAID"),
    ]
    session.add_all(invoices)

    # --- ERP: Payments (Bank Feed) ---
    payments = [
        # Match for INV-001
        Payment(date=date(2025, 1, 10), amount=1200.00, description="Payment for INV-001", reference_id="TXN-1001"),
        
        # Match for INV-002
        Payment(date=date(2025, 1, 12), amount=450.50, description="DesignStudio Inv 002", reference_id="TXN-1002"),
        
        # Match for INV-003 (Date + 2 days)
        Payment(date=date(2025, 1, 17), amount=3000.00, description="BigRetail Payment", reference_id="TXN-1003"),
        
        # Orphan Payment (No matching invoice)
        Payment(date=date(2025, 1, 25), amount=150.00, description="Unknown Incoming", reference_id="TXN-9999"),
    ]
    session.add_all(payments)

    session.commit()
    print("Database seeded with simulated CRM and ERP data!")
    session.close()

if __name__ == "__main__":
    seed_data()
