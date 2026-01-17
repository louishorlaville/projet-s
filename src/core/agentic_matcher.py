import json
import logging
from datetime import datetime
from src.core.llm_client import LLMClient

class AgenticMatcher:
    def __init__(self):
        self.llm = LLMClient()

    def smart_reconcile(self, invoices, payments):
        """
        Identify matches using LLM reasoning.
        """
        # 1. Pre-filtering: Only consider items that are not obviously mismatched by huge date diffs 
        # (Though for a small prototype, we can send all open items).
        
        if not invoices or not payments:
            return []

        # Prepare Data for Prompt
        invoices_str = json.dumps([{
            "id": inv['id'],
            "ref": inv['ref'], 
            "amount": float(inv['total_ttc']),
            "date": inv['date'], # Timestamp
            "customer_id": inv['socid']
        } for inv in invoices])

        payments_str = json.dumps([{
            "id": pay['id'],
            "label": pay['label'],
            "amount": float(pay['amount']),
            "date": pay['datev'] # Timestamp
        } for pay in payments])

        # System Prompt
        system_prompt = """
        You are an expert financial auditor and reconciliation agent.
        Your goal is to match Invoices to Bank Payments.
        
        Rules:
        1. Match based on Amount (exact or partial payments are acceptable).
        2. Match based on Entity Name (e.g. 'Photo Saint-Denis' similar to 'Payment from Photo St-Denis').
        3. Match based on Date (Payment usually shortly after Invoice).
        4. **Partial Payments**: If a payment amount is less than the invoice total, it's still a valid match (note this in the reason).
        5. One Payment can cover multiple Invoices (Sum logic).
        6. Set confidence score based on match quality:
           - 0.95-1.0 for exact matches
           - 0.80-0.94 for partial payments or fuzzy name matches
           - 0.60-0.79 for date mismatches but amount matches
        7. Return ONLY a JSON list of matches.
        
        Output Format:
        [
            {
                "invoice_id": 123,
                "payment_id": 456,
                "confidence": 0.95,
                "reason": "Exact amount match and name similarity."
            }
        ]
        If no matches found, return empty list [].
        Do not return markdown formatting, just raw JSON.
        """

        user_prompt = f"""
        Here are the Unpaid Invoices:
        {invoices_str}

        Here are the Unreconciled Payments:
        {payments_str}

        Find the matches.
        """

        print("🤖 Asking LLM to match...")
        response_text = self.llm.get_completion(system_prompt, user_prompt)
        
        if not response_text:
            return []

        # Parse JSON
        try:
            # Clean md code blocks if present
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            matches = json.loads(cleaned_text)
            return matches
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM JSON: {e}")
            print(f"Raw Response: {response_text}")
            return []

if __name__ == "__main__":
    # Test Stub
    pass
