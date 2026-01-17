import sys
import os
# import google.generativeai as genai # Moved inside class to avoid import if mock

# Ensure import paths work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.config import LLM_API_KEY, LLM_MODEL, LLM_PROVIDER

class LLMClient:
    def __init__(self):
        self.provider = LLM_PROVIDER
        self.api_key = LLM_API_KEY
        
        if self.provider == "gemini":
            import google.generativeai as genai
            self.genai = genai  # Store as instance variable
            self.genai.configure(api_key=self.api_key)
            self.model = self.genai.GenerativeModel(LLM_MODEL)
        elif self.provider == "mock":
            print("⚠️ Using Mock LLM Client")
        
    def get_completion(self, system_prompt, user_prompt):
        """
        Send a prompt to the LLM and get the response text.
        """
        if self.provider == "mock":
            # Simulate AI matching based on CURRENT Dolibarr data
            # Invoice 7 (IN2601-0001, $1200) -> Payment 7 ($1200)
            # Invoice 8 (IN2601-0002, $450) -> Payment 8 ($400 PARTIAL)
            # Invoice 9 (IN2502-0003, $450) -> Payment 9 ($450)
            # Payment 11 ($99) -> Orphan
            return """
            [
                {
                    "invoice_id": "7",
                    "payment_id": "7", 
                    "confidence": 0.98,
                    "reason": "Exact amount match (1200.00 CAD) between Invoice IN2601-0001 and bank line."
                },
                {
                    "invoice_id": "8",
                    "payment_id": "8",
                    "confidence": 0.85, 
                    "reason": "Partial payment detected: Invoice IN2601-0002 total $450, payment received $400. Remaining balance: $50."
                },
                {
                    "invoice_id": "9",
                    "payment_id": "9",
                    "confidence": 0.95, 
                    "reason": "Exact amount match (450.00 CAD) between Invoice IN2502-0003 and bank line."
                }
            ]
            """

        try:
            full_prompt = f"{system_prompt}\n\nUser Query: {user_prompt}"
            response = self.model.generate_content(
                full_prompt,
                generation_config=self.genai.types.GenerationConfig(
                    temperature=0.0 # Deterministic
                )
            )
            return response.text
        except Exception as e:
            print(f"LLM Error: {e}")
            return None

if __name__ == "__main__":
    # Test
    client = LLMClient()
    print("Testing Gemini Connection...")
    res = client.get_completion("You are a helpful assistant.", "Say 'Hello, Agent!'")
    print(f"Response: {res}")
