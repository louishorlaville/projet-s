import sys
import os
from datetime import date, timedelta, datetime
import random

# Ensure import paths work if run directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.integrations.dolibarr import DolibarrClient

def seed_dolibarr():
    print("🚀 Starting Dolibarr Live Seeder...")
    client = DolibarrClient()

    # 1. Fetch Existing Third Parties
    print("\n--- Fetching Third Parties ---")
    tiers = client.get_thirdparties()
    
    if not tiers or len(tiers) < 2:
        print("❌ Error: Need at least 2 Third Parties in Dolibarr to run this seed script.")
        print("Please create 'Photo Saint-Denis' and 'Groupe Sportscene Inc' manually in Dolibarr first.")
        return

    # Assuming User followed instructions:
    # T1 = Photo Saint-Denis
    # T2 = Groupe Sportscene Inc (La Cage)
    # We'll just grab the first two generic ones if names don't match, or try to find by name.
    
    t1 = tiers[0]
    t2 = tiers[1]
    
    id_photo = t1['id']
    id_cage = t2['id']
    
    print(f"✅ Using Third Party 1: {t1.get('name')} (ID: {id_photo})")
    print(f"✅ Using Third Party 2: {t2.get('name')} (ID: {id_cage})")

    # 2. Create Bank Account
    print("\n--- Creating Bank Account ---")
    accounts = client.get_bank_accounts()
    
    bank_id = None
    # Check if our specific CAD account exists
    for acc in accounts:
        if acc.get('ref') == 'BANK-CAD':
            bank_id = acc['id']
            print(f"ℹ️ Using existing Bank Account: {acc['label']} (ID: {bank_id})")
            break
            
    if not bank_id:
        bank_data = {
           "ref": "BANK-CAD",
           "label": "Main Corporate Account (CAD)",
           "bancaire": "1",
           "currency_code": "CAD",
           "country_id": "14", # 14 = Canada (Common ID, adjust if needed)
           "type": 1, 
           "status": 1
        }
        bank_id = client._post("/bankaccounts", bank_data)
        if bank_id:
            print(f"✅ Created Bank Account (ID: {bank_id})")
        else:
            print("❌ Failed to create Bank Account. Check logs.")
            return # Stop execution if no bank account

    # 3. Create Invoices
    print("\n--- Creating Invoices ---")
    
    # Invoice 1 for Photo Saint-Denis
    if id_photo:
        inv1_data = {
            "socid": id_photo,
            "date": int(datetime.now().timestamp()),
            "type": 0,
            "lines": [
                {
                    "desc": "Photography Services",
                    "subprice": 1000.00,
                    "tva_tx": 20.00,
                    "qty": 1
                }
            ]
        }
        inv1_id = client._post("/invoices", inv1_data)
        if inv1_id:
            print(f"✅ Created Invoice for Photo Saint-Denis (ID: {inv1_id})")
            # Validate it
            client._post(f"/invoices/{inv1_id}/validate", {"idwarehouse": 0})
            print(f"   Validated Invoice {inv1_id}")

    # Invoice 2 for La Cage
    if id_cage:
        inv2_data = {
            "socid": id_cage,
            "date": int(datetime.now().timestamp()),
            "type": 0,
            "lines": [
                {
                    "desc": "Catering Services",
                    "subprice": 450.00,
                    "tva_tx": 0.00,
                    "qty": 1
                }
            ]
        }
        inv2_id = client._post("/invoices", inv2_data)
        if inv2_id:
            print(f"✅ Created Invoice for La Cage (ID: {inv2_id})")
            client._post(f"/invoices/{inv2_id}/validate", {"idwarehouse": 0})
            print(f"   Validated Invoice {inv2_id}")

    # 4. Create Bank Transactions (Lines)
    print("\n--- Creating Bank Transactions ---")
    
    # Transaction 1: Match for Photo Saint-Denis (1200)
    txn1 = {
        "date": int(datetime.now().timestamp()),
        "type": "VIR",
        "label": "Payment from Photo Saint-Denis",
        "amount": 1200.00
    }
    client._post(f"/bankaccounts/{bank_id}/lines", txn1)
    print("✅ Created Transaction: +1200.00 (Match Photo Saint-Denis)")
    
    # Transaction 2: Match for La Cage (450)
    txn2 = {
        "date": int(datetime.now().timestamp()),
        "type": "VIR",
        "label": "Transfer from La Cage",
        "amount": 450.00
    }
    client._post(f"/bankaccounts/{bank_id}/lines", txn2)
    print("✅ Created Transaction: +450.00 (Match La Cage)")
    
    # Transaction 3: Orphan / Ghost
    txn3 = {
        "date": int(datetime.now().timestamp()),
        "type": "VIR",
        "label": "Unknown Payment X",
        "amount": 99.00
    }
    client._post(f"/bankaccounts/{bank_id}/lines", txn3)
    print("✅ Created Transaction: +99.00 (Orphan)")

    print("\n\n🎉 Done! Dolibarr is now populated with test data.")

if __name__ == "__main__":
    seed_dolibarr()
