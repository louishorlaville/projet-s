import requests
import sys
import os

# Adapt path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.config import DOLIBARR_API_URL, DOLIBARR_API_KEY

class DolibarrClient:
    def __init__(self):
        self.base_url = DOLIBARR_API_URL
        self.headers = {
            "DOLAPIKEY": DOLIBARR_API_KEY,
            "Accept": "application/json"
        }

    def _get(self, endpoint, params=None):
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            print(f"Response: {response.text}")
            return []
        except Exception as e:
            print(f"Error connecting to Dolibarr: {e}")
            return []

    def get_thirdparties(self):
        """Fetch all third parties (clients/prospects)"""
        return self._get("/thirdparties")

    def get_unpaid_invoices(self):
        """Fetch invoices with status=unpaid (status property might vary, usually 'statut' or 'paye')"""
        # Status "0" = Draft, "1" = Unpaid, "2" = Paid, "3" = Abandoned
        # We want validated (1) and unpaid (paye=0)
        # Dolibarr filtering syntax is SQL-like in some versions, or query params
        # Simple param: sqlfilters=(t.paye:=:0)
        
        # Determine correct filter based on API version. 
        # For now, fetch all and filter in python if API filter is tricky
        invoices = self._get("/invoices", params={"sortfield": "t.rowid", "sortorder": "ASC", "limit": 100})
        
        # Filter for Unpaid: paye == 0 AND status == 1 (Validated)
        unpaid = [inv for inv in invoices if inv.get('status') == '1' and inv.get('paye') == '0']
        return unpaid

    def get_bank_accounts(self):
        """Fetch all bank accounts"""
        return self._get("/bankaccounts")

    def get_bank_lines(self, account_id):
        """Fetch transactions for a specific bank account"""
        return self._get(f"/bankaccounts/{account_id}/lines")

if __name__ == "__main__":
    client = DolibarrClient()
    
    print("--- Testing Connection: Third Parties ---")
    tiers = client.get_thirdparties()
    for t in tiers:
        print(f"Found: {t.get('name')} (ID: {t.get('id')})")
        
    print("\n--- Testing: Bank Accounts ---")
    accounts = client.get_bank_accounts()
    for acc in accounts:
        print(f"Account: {acc.get('label')} (ID: {acc.get('id')})")
