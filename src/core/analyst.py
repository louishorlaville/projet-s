import json
import logging
from typing import List, Dict, Any
from src.config import LLM_API_KEY, LLM_MODEL

# LangChain Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

class Anomaly(BaseModel):
    id: str = Field(description="Unique ID of the transaction (Invoice or Payment ID)")
    type: str = Field(description="Type of anomaly: 'CURRENCY_MISMATCH', 'TAX_ERROR', 'PRICE_DISCREPANCY', or 'OTHER'")
    severity: str = Field(description="Severity level: 'HIGH', 'MEDIUM', 'LOW'")
    description: str = Field(description="Detailed explanation of the anomaly")
    recommendation: str = Field(description="Suggested action for the user")

class FinancialAnalyst:
    def __init__(self):
        if not LLM_API_KEY:
            raise ValueError("LLM_API_KEY is not set in config.")
        
        self.llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=LLM_API_KEY,
            temperature=0.0
        )
        
        self.parser = JsonOutputParser(pydantic_object=Anomaly)

    def analyze_matches(self, matches: List[Dict], invoices: List[Dict], payments: List[Dict]) -> List[Dict]:
        """
        Deep dive analysis of matched transactions to find complex anomalies.
        """
        if not matches:
            return []

        # 1. Enrich matches with full data
        enriched_data = []
        
        # Create lookups
        inv_lookup = {str(i['id']): i for i in invoices}
        pay_lookup = {str(p['id']): p for p in payments}

        for match in matches:
            inv_id = str(match['invoice_id'])
            pay_id = str(match['payment_id'])
            
            if inv_id in inv_lookup and pay_id in pay_lookup:
                inv = inv_lookup[inv_id]
                pay = pay_lookup[pay_id]
                
                enriched_data.append({
                    "match_id": f"{inv_id}-{pay_id}",
                    "invoice": {
                        "ref": inv.get('ref'),
                        "amount": inv.get('total_ttc'),
                        "currency": inv.get('multicurrency_code', 'CAD'), # Default to CAD if missing
                        "total_tax": inv.get('total_tva'),
                        "date": inv.get('date')
                    },
                    "payment": {
                        "label": pay.get('label'),
                        "amount": pay.get('amount'),
                        "currency": pay.get('multicurrency_code', 'CAD'), # Default to CAD
                        "date": pay.get('datev')
                    }
                })

        if not enriched_data:
            return []

        # 2. Construct Prompt
        template = """
        You are a Senior Financial Forensic Analyst.
        Analyze the following RECONCILED transactions for complex anomalies.

        YOUR GOAL:
        Detect specific financial irregularities that simple matching missed.

        ASPECTS TO ANALYZE:
        1. 💱 CURRENCY MISMATCH: Invoice in one currency (e.g. USD), Payment in another (e.g. CAD). calculate if the exchange rate makes sense.
        2. 🏛️ TAX ANOMALIES: Is the tax amount (`total_tax`) roughly consistent with standard rates (e.g. 5%, 15%, 20%)? If tax is 0 but it looks like a taxable service, flag it.
        3. 💸 PRICE DISCREPANCY: Significant difference (> 2%) between Invoice Amount and Payment Amount. 
           - Small differences could be bank fees (Low Severity).
           - Large differences could be underpayment (High Severity).

        INPUT DATA:
        {data}

        OUTPUT FORMAT:
        Return a JSON list of identified anomalies.
        {format_instructions}

        If no anomalies are found, return an empty list [].
        """

        prompt = PromptTemplate(
            template=template,
            input_variables=["data"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

        chain = prompt | self.llm | self.parser

        print("🕵️‍♀️ Financial Analyst conducting deep dive...")

        try:
            # specialized analysis might be token heavy, so we might need to batch in future
            # for now, send all
            response = chain.invoke({"data": json.dumps(enriched_data)})
            
            # Ensure it's a list
            if isinstance(response, dict):
                return [response]
            return response
            
        except Exception as e:
            print(f"❌ Analyst Error: {e}")
            return []

if __name__ == "__main__":
    pass
