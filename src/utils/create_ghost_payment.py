"""
Create a Ghost Payment scenario:
- Invoice marked as PAID in Dolibarr
- But no corresponding bank transaction
"""

import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.integrations.dolibarr import DolibarrClient

def create_ghost_payment_invoice():
    """Create an invoice for manual Ghost Payment testing."""
    client = DolibarrClient()
    
    # Get first third party
    parties = client.get_thirdparties()
    if not parties:
        print("❌ No third parties found. Cannot create invoice.")
        return
    
    thirdparty_id = parties[0]['id']
    thirdparty_name = parties[0]['name']
    
    print(f"Creating test invoice for: {thirdparty_name}")
    
    # Create invoice
    invoice_data = {
        "socid": thirdparty_id,
        "type": 0,  # Standard invoice
        "date": int(datetime.now().timestamp()),
        "lines": [
            {
                "desc": "Test Service - Ghost Payment Scenario",
                "subprice": 250.00,
                "qty": 1,
                "tva_tx": 0
            }
        ]
    }
    
    print("📝 Creating invoice...")
    invoice = client._post("/invoices", invoice_data)
    
    if not invoice:
        print("❌ Failed to create invoice")
        return
    
    invoice_id = invoice
    print(f"✅ Invoice created with ID: {invoice_id}")
    
    # Validate invoice
    print("✅ Validating invoice...")
    validation = client._post(f"/invoices/{invoice_id}/validate")
    
    if validation:
        print(f"✅ Invoice validated successfully!")
        print(f"\n📋 Next steps to create GHOST PAYMENT:")
        print(f"   1. Go to http://localhost:8080")
        print(f"   2. Navigate to the invoice (ID: {invoice_id})")
        print(f"   3. Click 'Classify Paid' manually")
        print(f"   4. Do NOT create a bank transaction")
        print(f"   5. Refresh the Streamlit app")
        print(f"   6. The audit should detect this as 🔴 GHOST_PAYMENT")
    else:
        print("❌ Failed to validate invoice")

if __name__ == "__main__":
    create_ghost_payment_invoice()
