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

def generate_recording_signature_and_test():
    """Generate Twilio signature for recording webhook and test it"""
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

    return {
        "url": webhook_url,
        "signature": twilio_signature,
        "payload": mock_recording_data,
        "auth_token_preview": auth_token[:8] + "..." if auth_token != "YOUR_AUTH_TOKEN" else auth_token
    }

def test_recording_webhook():
    """Test the recording webhook with generated signature"""
    result = generate_recording_signature_and_test()
    
    # Send the request
    headers = {
        "X-Twilio-Signature": result["signature"],
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(
            result["url"],
            data=urlencode(result["payload"]),
            headers=headers
        )
        
        return {
            "status_code": response.status_code,
            "response_text": response.text,
            "success": response.status_code == 200
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }

if __name__ == "__main__":
    # Only print when run directly for testing
    result = generate_recording_signature_and_test()
    print("URL being signed:", result["url"])
    print("Generated X-Twilio-Signature:", result["signature"])
    print("Auth Token used:", result["auth_token_preview"])
    print("\nPayload:")
    for key, value in result["payload"].items():
        print(f"  {key}: {value}")
    
    # Test the webhook
    test_result = test_recording_webhook()
    print(f"\nStatus Code: {test_result.get('status_code', 'Error')}")
    print(f"Response: {test_result.get('response_text', test_result.get('error', 'Unknown error'))}")
    
    if test_result.get("success"):
        print("Success! Your webhook validation is working correctly.")
    else:
        print("Something went wrong. Check your server logs for details.")