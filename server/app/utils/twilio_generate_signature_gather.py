from twilio.request_validator import RequestValidator
import os
import hmac
import hashlib
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Récupérez votre TWILIO_AUTH_TOKEN (assurez-vous qu'il correspond à celui configuré dans votre application)
auth_token = os.getenv("TWILIO_AUTH_TOKEN", "YOUR_AUTH_TOKEN")

# L'URL complète de votre endpoint Gather tel qu'utilisé par Twilio.
# IMPORTANT : L'URL doit être exactement la même (schéma, domaine, chemin et même slash final éventuel)
url = os.getenv("WEBHOOK_BASE_URL", "https://your-ngrok-url.ngrok.io") + "/api/webhooks/twilio/gather"

# Exemple de paramètres transmis par Twilio dans une requête Gather.
params = {
    "CallSid": "CA49922628d9b67311ed7fb8669c6d646d",
    "Digits": "1"
}

# Instanciation du RequestValidator avec votre Auth Token
validator = RequestValidator(auth_token)

# Calcul de la signature
signature = validator.compute_signature(url, params)

print("Signature Gather:", signature)
