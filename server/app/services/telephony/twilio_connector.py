from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.request_validator import RequestValidator
import base64
import hmac
import hashlib
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union
import os
from dotenv import load_dotenv

from ...core.config import get_settings
from ...core.logging import get_logger

logger = get_logger("services.telephony.twilio_connector")
settings = get_settings()

# Load environment variables
load_dotenv()

class TwilioConnector:
    """Interface with Twilio API for phone call functionality"""
    
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.phone_number = settings.TWILIO_PHONE_NUMBER
        self.debug_mode = settings.DEBUG
        
        # Only initialize Twilio client if not in debug mode
        if not self.debug_mode:
            self.client = Client(self.account_sid, self.auth_token)
            self.validator = RequestValidator(self.auth_token)
        else:
            logger.info("🎭 TwilioConnector initialized in DEBUG mode - calls will be simulated")
            self.client = None
            self.validator = None
    
    def validate_webhook_signature(self, url: str, params: Dict[str, Any], signature: str) -> bool:
        """
        Validate that a webhook request is coming from Twilio
        
        Args:
            url: The full URL of the request
            params: The form parameters of the request
            signature: The X-Twilio-Signature header value
        
        Returns:
            bool: Whether the signature is valid
        """
        if self.debug_mode:
            logger.info("🎭 SIMULATING webhook signature validation (Debug Mode)")
            return True
        
        return self.validator.validate(url, params, signature)
    
    def make_call(
        self, 
        to_number: str, 
        from_number: Optional[str] = None,
        webhook_url: Optional[str] = None,
        status_callback_url: Optional[str] = None,
        record: bool = False,
        recording_status_callback: Optional[str] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Initiate a new outbound call
        
        Args:
            to_number: The phone number to call
            from_number: The phone number to call from (defaults to configured number)
            webhook_url: The URL Twilio should call when the call is answered
            status_callback_url: The URL Twilio should call when call status changes
            record: Whether to record the call
            recording_status_callback: The URL Twilio should call with recording updates
            timeout: Call timeout in seconds
        
        Returns:
            Dict: Twilio API response data
        """
        if self.debug_mode:
            return self._simulate_call(to_number, from_number, webhook_url, status_callback_url, record, timeout)
        
        try:
            from_number = from_number or self.phone_number
            
            call_params = {
                "to": to_number,
                "from_": from_number,
                "timeout": timeout
            }
            
            if webhook_url:
                call_params["url"] = webhook_url
            
            if status_callback_url:
                call_params["status_callback"] = status_callback_url
                call_params["status_callback_event"] = ["initiated", "ringing", "answered", "completed"]
                call_params["status_callback_method"] = "POST"
            
            if record:
                call_params["record"] = True
                
                # Use recording_status_callback if provided, otherwise fall back to status_callback_url
                callback_url = recording_status_callback or status_callback_url
                if callback_url:
                    call_params["recording_status_callback"] = callback_url
                    call_params["recording_status_callback_method"] = "POST"
                    call_params["recording_status_callback_event"] = ["in-progress", "completed"]
            
            # Make the call
            call = self.client.calls.create(**call_params)
            
            logger.info(f"Call initiated to {to_number}, SID: {call.sid}")
            
            return {
                "sid": call.sid,
                "status": call.status,
                "direction": call.direction,
                "from_number": from_number,
                "to_number": to_number
            }
            
        except Exception as e:
            logger.error(f"Error making call to {to_number}: {str(e)}", exc_info=True)
            raise

    def _simulate_call(self, to_number: str, from_number: Optional[str], webhook_url: Optional[str], 
                      status_callback_url: Optional[str], record: bool, timeout: int) -> Dict[str, Any]:
        """
        Simulate a Twilio call for debug mode
        """
        from_number = from_number or self.phone_number
        logger.info(f"🎭 SIMULATING call to {to_number} from {from_number} (Debug Mode)")
        logger.info(f"   Webhook URL: {webhook_url}")
        logger.info(f"   Status Callback: {status_callback_url}")
        logger.info(f"   Recording: {record}")
        logger.info(f"   Timeout: {timeout}s")
        
        # Generate a fake call SID
        fake_call_sid = f"CA{uuid.uuid4().hex[:32]}"
        
        return {
            "sid": fake_call_sid,
            "status": "initiated",
            "direction": "outbound-api",
            "from_number": from_number,
            "to_number": to_number,
            "debug_mode": True,
            "note": "This is a simulated call for development purposes"
        }
    
    def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """
        Get the status of a call
        
        Args:
            call_sid: The Twilio call SID
        
        Returns:
            Dict: Call status information
        """
        if self.debug_mode and call_sid.startswith('CA'):
            return self._simulate_call_status(call_sid)
        
        try:
            call = self.client.calls(call_sid).fetch()
            
            return {
                "sid": call.sid,
                "status": call.status,
                "direction": call.direction,
                "duration": call.duration,
                "start_time": call.start_time,
                "end_time": call.end_time
            }
            
        except Exception as e:
            logger.error(f"Error getting call status for {call_sid}: {str(e)}", exc_info=True)
            raise

    def _simulate_call_status(self, call_sid: str) -> Dict[str, Any]:
        """
        Simulate call status for debug mode
        """
        logger.info(f"🎭 SIMULATING call status for {call_sid} (Debug Mode)")
        return {
            "sid": call_sid,
            "status": "completed",
            "direction": "outbound-api",
            "duration": 30,
            "start_time": datetime.utcnow(),
            "end_time": datetime.utcnow(),
            "debug_mode": True
        }
    
    def end_call(self, call_sid: str) -> bool:
        """
        End an in-progress call
        
        Args:
            call_sid: The Twilio call SID
        
        Returns:
            bool: Whether the call was successfully ended
        """
        if self.debug_mode and call_sid.startswith('CA'):
            logger.info(f"🎭 SIMULATING call end for {call_sid} (Debug Mode)")
            return True
        
        try:
            call = self.client.calls(call_sid).update(status="completed")
            logger.info(f"Call {call_sid} ended")
            return True
            
        except Exception as e:
            logger.error(f"Error ending call {call_sid}: {str(e)}", exc_info=True)
            return False
    
    def get_recording_url(self, recording_sid: str) -> str:
        """
        Get the URL for a call recording
        
        Args:
            recording_sid: The Twilio recording SID
        
        Returns:
            str: Recording URL
        """
        try:
            recording = self.client.recordings(recording_sid).fetch()
            return recording.uri
            
        except Exception as e:
            logger.error(f"Error getting recording URL for {recording_sid}: {str(e)}", exc_info=True)
            raise
    
    def generate_welcome_twiml(self, welcome_message: Optional[str] = None) -> str:
        """
        Generate TwiML for the initial welcome message and survey start
        
        Args:
            welcome_message: Custom welcome message (optional)
        
        Returns:
            str: TwiML XML string
        """
        webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "https://your-ngrok-url.ngrok.io")
        
        response = VoiceResponse()
        
        if not welcome_message:
            welcome_message = "Hello! Thank you for participating in our survey. Let's get started."
        
        response.say(welcome_message)
        
        # Add a pause
        response.pause(length=1)
        
        # Add gather for the first question - webhook for this will serve the first question
        gather = Gather(
            input='dtmf speech',
            action=f'{webhook_base_url}/api/webhooks/twilio/gather',
            method='POST',
            speech_timeout='auto',
            enhanced='true',
            language='en-US'
        )
        
        gather.say("Please press any key or say something when you're ready to begin.")
        
        response.append(gather)
        
        # Add a fallback if no input is received
        response.say("I didn't receive any input. Let's try again.")
        response.redirect(f'{webhook_base_url}/api/webhooks/twilio/voice')
        
        return str(response)
    
    def generate_question_twiml(self, question_text: str, question_type: str = "open_ended", options: list = None) -> str:
        """
        Generate TwiML for asking a survey question
        
        Args:
            question_text: The question to ask
            question_type: Type of question (open_ended, numeric, yes_no, multiple_choice)
            options: List of options for multiple choice questions
        
        Returns:
            str: TwiML XML string
        """
        webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "https://your-ngrok-url.ngrok.io")
        
        response = VoiceResponse()
        
        # Customize gather based on question type
        if question_type == "numeric":
            # For numeric ratings, allow both DTMF and speech input
            gather = Gather(
                input='dtmf speech',
                num_digits=1,
                action=f'{webhook_base_url}/api/webhooks/twilio/gather',
                method='POST',
                timeout=15,
                speech_timeout='auto',
                enhanced='true',
                language='en-US'
            )
            
            gather.say(f"{question_text} You can press a number from 1 to 5 on your keypad, or simply say your rating.")
            response.append(gather)
            
            # Fallback for no input
            response.say("I didn't receive your rating. Let's try again.")
            response.redirect(f'{webhook_base_url}/api/webhooks/twilio/gather')
            
        elif question_type == "yes_no":
            # For yes/no questions, allow both DTMF (1=yes, 2=no) and speech
            gather = Gather(
                input='dtmf speech',
                action=f'{webhook_base_url}/api/webhooks/twilio/gather',
                method='POST',
                timeout=10,
                speech_timeout='auto',
                enhanced='true',
                language='en-US'
            )
            
            gather.say(f"{question_text} Press 1 for yes or 2 for no, or simply say yes or no.")
            response.append(gather)
            
            # Fallback for no input
            response.say("I didn't receive your answer. Let's try again.")
            response.redirect(f'{webhook_base_url}/api/webhooks/twilio/gather')
            
        elif question_type == "multiple_choice":
            # For multiple choice, allow DTMF input based on the number of options
            gather = Gather(
                input='dtmf speech',
                action=f'{webhook_base_url}/api/webhooks/twilio/gather',
                method='POST',
                timeout=15,
                speech_timeout='auto',
                enhanced='true',
                language='en-US'
            )
            
            # Build the complete question with numbered options
            complete_question = question_text
            if options and len(options) > 0:
                complete_question += " Your options are: "
                for i, option in enumerate(options, 1):
                    complete_question += f"Press {i} for {option}. "
                complete_question += "Please press a number from 1 to " + str(len(options)) + "."
            else:
                complete_question += " Please press a number to select your choice."
            
            gather.say(complete_question)
            response.append(gather)
            
            # Fallback for no input
            response.say("I didn't receive your selection. Let's try again.")
            response.redirect(f'{webhook_base_url}/api/webhooks/twilio/gather')
            
        else:  # Default to open-ended
            # For open-ended questions, we want speech input
            gather = Gather(
                input='speech',
                action=f'{webhook_base_url}/api/webhooks/twilio/gather',
                method='POST',
                timeout=15,
                speech_timeout='auto',
                enhanced='true',
                language='en-US'
            )
            
            gather.say(question_text)
            response.append(gather)
            
            # Fallback for no input
            response.say("I didn't hear your response. Let's try again.")
            response.redirect(f'{webhook_base_url}/api/webhooks/twilio/gather')
        
        return str(response)
    
    def generate_end_survey_twiml(self, outro_message: Optional[str] = None) -> str:
        """
        Generate TwiML for ending a survey
        
        Args:
            outro_message: The message to say at the end of the survey
        
        Returns:
            str: TwiML XML string
        """
        response = VoiceResponse()
        
        if not outro_message:
            outro_message = "Thank you for participating in our survey! Your feedback is valuable to us. Goodbye."
        
        response.say(outro_message)
        
        # Add a pause and then hang up
        response.pause(length=1)
        response.hangup()
        
        return str(response)
    
    def generate_error_twiml(self, error_message: str) -> str:
        """
        Generate TwiML for error handling
        
        Args:
            error_message: The error message to say
        
        Returns:
            str: TwiML XML string
        """
        response = VoiceResponse()
        
        response.say(f"I'm sorry, but there was an error with the survey. {error_message}")
        response.say("Please try again later. Goodbye.")
        response.hangup()
        
        return str(response)

def create_survey_twiml(survey, webhook_base_url=None):
    """Generate TwiML for survey questions"""
    if webhook_base_url is None:
        webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "https://your-ngrok-url.ngrok.io")
    
    # ... existing code ...
    
    gather = Gather(
        input='dtmf speech',
        action=f'{webhook_base_url}/api/webhooks/twilio/gather',
        method='POST',
        timeout=10,
        speech_timeout='auto'
    )
    
    # ... existing code ...
    
    response.redirect(f'{webhook_base_url}/api/webhooks/twilio/voice')
    
    # ... existing code ...