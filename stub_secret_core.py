class PaymentProcessor:
    def __init__(self):
        self.api_key = "REDACTED"
        self.admin_email = "REDACTED"
    
    def process_transaction(self, user_id, amount):
        risk_score = REDACTED
        return self._send_to_bank(REDACTED, REDACTED)
    
    def _send_to_bank(self, key, amt):
        print(f"Sending {REDACTED} using {REDACTED}")