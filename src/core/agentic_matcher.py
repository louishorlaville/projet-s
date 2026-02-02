import json
import logging
import os
from datetime import datetime
from src.config import LLM_API_KEY, LLM_MODEL

# LangChain Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class AgenticMatcher:
    def __init__(self):
        # Initialize Google GenAI via LangChain
        if not LLM_API_KEY:
            raise ValueError("LLM_API_KEY is not set in config.")
        
        self.llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=LLM_API_KEY,
            temperature=0.0
        )
        
        # Define output parser
        self.parser = JsonOutputParser()

    def smart_reconcile(self, invoices, payments):
        """
        Identify matches using LLM reasoning via LangChain.
        """
        if not invoices or not payments:
            return []

        # Prepare Data
        # Filter fields to reduce token usage
        clean_invoices = [{
            "id": inv['id'],
            "ref": inv.get('ref'), 
            "amount": float(inv.get('total_ttc', 0)),
            "date": inv.get('date'), 
            "customer": inv.get('Customer', inv.get('socid'))
        } for inv in invoices]

        clean_payments = [{
            "id": pay['id'],
            "label": pay.get('label'),
            "amount": float(pay.get('amount', 0)),
            "date": pay.get('datev') 
        } for pay in payments]

        # Template
        template = """
        You are an expert financial reconciliation agent.
        Your goal is to match Invoices to Bank Payments.

        RULES:
        1. Match by AMOUNT (Exact or Partial).
        2. Match by ENTITY NAME (Fuzzy matching allowed).
        3. Match by DATE (Payment date is usually close to invoice date).
        4. PARTIAL PAYMENTS: Valid if Payment < Invoice.
        5. SUM LOGIC: One payment can cover multiple invoices.

        CONFIDENCE SCORING:
        - 0.95 - 1.00: Exact Match (Amount + Name + Date)
        - 0.85 - 0.94: Partial Payment or Minor Date/Name Diff
        - 0.70 - 0.84: Likely Match (Major Date Diff or Name Diff)

        INPUT DATA:
        Invoices: {invoices}
        
        Payments: {payments}

        OUTPUT FORMAT:
        Return ONLY a JSON list (no markdown).
        [
            {{
                "invoice_id": "ID",
                "payment_id": "ID",
                "confidence": 0.95,
                "reason": "Explanation"
            }}
        ]
        If no matches, return [].
        """

        prompt = PromptTemplate(
            template=template,
            input_variables=["invoices", "payments"]
        )

        # Create Chain
        chain = prompt | self.llm | self.parser

        print("🔗 LangChain Agent reconciling...")
        
        try:
            matches = chain.invoke({
                "invoices": json.dumps(clean_invoices),
                "payments": json.dumps(clean_payments)
            })
            return matches
        except Exception as e:
            print(f"❌ LangChain Error: {e}")
            return []

if __name__ == "__main__":
    pass
