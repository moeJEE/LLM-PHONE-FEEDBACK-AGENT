import hmac
import hashlib
import os
from dotenv import load_dotenv
from twilio.request_validator import RequestValidator

# Load environment variables
load_dotenv()

def generate_twilio_signature():
    """Generate Twilio signature for webhook validation testing"""
    # Auth token Twilio (à garder secret)
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "YOUR_AUTH_TOKEN")

    # URL cible de la requête webhook (utilise la variable d'environnement)
    url = os.getenv("LOCAL_SERVER_URL", "http://localhost:8000") + "/api/webhooks/twilio/voice"

    # Les paramètres envoyés dans le corps de la requête POST
    params = {
        "CallSid": "CA123456789",
        "Digits": "1",
        "From": "+15551234567"
    }

    # Génération de la signature
    validator = RequestValidator(auth_token)
    signature = validator.compute_signature(url, params)

    return signature

if __name__ == "__main__":
    # Only print when run directly for testing
    signature = generate_twilio_signature()
    print(f'X-Twilio-Signature: {signature}')
