import requests
import hmac
import hashlib
import base64
from urllib.parse import urlencode, urlparse, parse_qs
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Your Twilio credentials from environment variables
account_sid = os.getenv("TWILIO_ACCOUNT_SID", "YOUR_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN", "YOUR_AUTH_TOKEN")

# Your webhook URL - make sure this exactly matches what's in your server config
webhook_url = os.getenv("WEBHOOK_BASE_URL", "https://your-ngrok-url.ngrok.io") + "/api/webhooks/twilio/recording-callback"

# The call you want to simulate a recording for
call_sid = "CA8857efae1ee5e7e37e674dbdf94b12ed"

# Create a mock recording payload (similar to what Twilio would send)
mock_recording_data = {
    "AccountSid": account_sid,
    "CallSid": call_sid,
    "RecordingSid": "RE" + "0" * 32,  # Fake recording SID
    "RecordingUrl": f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Recordings/RE000000000000000000000000000000.mp3",
    "RecordingStatus": "completed",
    "RecordingDuration": "15",
    "RecordingChannels": "1",
    "RecordingStartTime": "2025-04-12T18:42:40Z",
    "RecordingSource": "OutboundAPI",
    "RecordingTrack": "both"
}

# Function to generate Twilio signature (following Twilio's exact method)
def generate_twilio_signature(url, params):
    # Ensure URL has no query parameters
    parsed_url = urlparse(url)
    base_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
    
    # Create a string of all params sorted by key
    # This is EXACTLY how Twilio does it
    valueString = ""
    for k in sorted(params.keys()):
        valueString += k + params[k]
    
    # Combine URL and params
    data = base_url + valueString
    
    # Create the HMAC-SHA1 signature
    hmac_obj = hmac.new(
        key=auth_token.encode('utf-8'),
        msg=data.encode('utf-8'),
        digestmod=hashlib.sha1
    )
    
    # Get the digest and encode in base64
    return base64.b64encode(hmac_obj.digest()).decode()

# Generate the Twilio signature
twilio_signature = generate_twilio_signature(webhook_url, mock_recording_data)

# Print information for debugging
print("URL being signed:", webhook_url)
print("Generated X-Twilio-Signature:", twilio_signature)
print("Auth Token used:", auth_token[:8] + "..." if auth_token != "YOUR_AUTH_TOKEN" else auth_token)
print("\nPayload:")
for key, value in mock_recording_data.items():
    print(f"  {key}: {value}")

# Send the request
headers = {
    "X-Twilio-Signature": twilio_signature,
    "Content-Type": "application/x-www-form-urlencoded"
}

try:
    response = requests.post(
        webhook_url,
        data=urlencode(mock_recording_data),
        headers=headers
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("Success! Your webhook validation is working correctly.")
    else:
        print("Something went wrong. Check your server logs for details.")
        
except Exception as e:
    print(f"Error sending request: {e}")