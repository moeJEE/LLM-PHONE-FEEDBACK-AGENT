import hmac
import hashlib
import os
from dotenv import load_dotenv
from twilio.request_validator import RequestValidator

# Load environment variables
load_dotenv()

auth_token = os.getenv("TWILIO_AUTH_TOKEN", "YOUR_AUTH_TOKEN")

# L'URL exacte que Twilio utilise pour appeler votre webhook
url = os.getenv("WEBHOOK_BASE_URL", "https://your-ngrok-url.ngrok.io") + "/api/webhooks/twilio/voice"

# Exemple de paramètres envoyés par Twilio (ils doivent être exactement ceux de votre payload)
params = {
    "CallSid": "CA49922628d9b67311ed7fb8669c6d646d",
    "CallStatus": "ringing"
}

# Instanciation du RequestValidator avec le secret
validator = RequestValidator(auth_token)

# Calcul de la signature
signature = validator.compute_signature(url, params)
print("Signature calculée :", signature)
