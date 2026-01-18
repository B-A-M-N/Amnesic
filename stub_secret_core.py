class PaymentProcessor:
    def __init__(self):
        self.api_key = 'REDACTED'
        self.admin_email = 'REDACTED'
    
    def process_transaction(self, user_id, amount):
        # REDACTED
        risk_score = 'REDACTED'
        return self._send_to_bank(self.api_key, amount)
    
    def _send_to_bank(self, key, amt):
        # REDACTED
        print('REDACTED')