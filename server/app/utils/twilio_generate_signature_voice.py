import hmac
import hashlib
import os
from dotenv import load_dotenv
from twilio.request_validator import RequestValidator

# Load environment variables
load_dotenv()

def generate_voice_signature():
    """Generate Twilio signature for voice webhook validation testing"""
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "YOUR_AUTH_TOKEN")

    # L'URL exacte que Twilio utilise pour appeler votre webhook
    url = os.getenv("WEBHOOK_BASE_URL", "https://your-ngrok-url.ngrok.io") + "/api/webhooks/twilio/voice"

    # Exemple de paramètres envoyés par Twilio (ils doivent être exactement ceux de votre payload)
    params = {
        "CallSid": "CA49922628d9b67311ed7fb8669c6d646d",
        "Caller": "+15551234567",
        "Digits": "1",
        "From": "+15551234567",
        "To": "+15559876543"
    }

    # Génère la signature avec RequestValidator
    validator = RequestValidator(auth_token)
    signature = validator.compute_signature(url, params)
    
    return signature

if __name__ == "__main__":
    # Only print when run directly for testing
    signature = generate_voice_signature()
    print("Signature calculée :", signature)
