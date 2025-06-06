from twilio.request_validator import RequestValidator
import os
import hmac
import hashlib
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_gather_signature():
    """Generate Twilio signature for gather webhook validation testing"""
    # Récupérez votre TWILIO_AUTH_TOKEN (assurez-vous qu'il correspond à celui configuré dans votre application)
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "YOUR_AUTH_TOKEN")

    # L'URL complète de votre endpoint Gather tel qu'utilisé par Twilio.
    # IMPORTANT : L'URL doit être exactement la même (schéma, domaine, chemin et même slash final éventuel)
    url = os.getenv("WEBHOOK_BASE_URL", "https://your-ngrok-url.ngrok.io") + "/api/webhooks/twilio/gather"

    # Exemple de paramètres transmis par Twilio dans une requête Gather.
    params = {
        "CallSid": "CA49922628d9b67311ed7fb8669c6d646d",
        "Digits": "1",
        "From": "+15551234567"
    }

    # Génération de la signature à l'aide de RequestValidator
    validator = RequestValidator(auth_token)
    signature = validator.compute_signature(url, params)
    
    return signature

if __name__ == "__main__":
    # Only print when run directly for testing
    signature = generate_gather_signature()
    print("Signature Gather:", signature)
