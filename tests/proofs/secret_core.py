
class PaymentProcessor:
    def __init__(self):
        self.api_key = "REDACTED" # SECRET!
        self.admin_email = "REDACTED" # PII!
    
    def process_transaction(self, user_id, amount):
        # Proprietary Algorithm
        risk_score = (amount * 0.05) + 42 
        return self._send_to_bank(self.api_key, amount)
    
    def _send_to_bank(self, key, amt):
        print(f"Sending {amt} using {key}")
