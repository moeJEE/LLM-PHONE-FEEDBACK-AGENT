"""
WhatsApp service for sending business-initiated messages using Twilio
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
import json

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self.debug_mode = self.settings.DEBUG
        
    @property
    def client(self) -> Client:
        if self._client is None:
            try:
                # Log credentials being used (first few characters only for security)
                logger.info(f"🔧 Initializing Twilio WhatsApp client with Account SID: {self.settings.TWILIO_ACCOUNT_SID[:8]}...")
                logger.info(f"🔧 Auth Token starts with: {self.settings.TWILIO_AUTH_TOKEN[:8]}...")
                
                self._client = Client(
                    self.settings.TWILIO_ACCOUNT_SID,
                    self.settings.TWILIO_AUTH_TOKEN
                )
                # Test the connection
                if not self.debug_mode:
                    try:
                        account = self._client.api.accounts(self.settings.TWILIO_ACCOUNT_SID).fetch()
                        logger.info(f"✅ Twilio WhatsApp client initialized successfully. Account status: {account.status}")
                    except TwilioRestException as e:
                        logger.error(f"❌ Twilio account verification failed: {e.msg} (Code: {e.code})")
                        logger.error(f"❌ Error details: {e.details}")
                        raise e
                    logger.info("✅ Twilio WhatsApp client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Twilio WhatsApp client: {e}")
                if self.debug_mode:
                    logger.warning("🔧 Running in DEBUG mode - WhatsApp messages will be simulated")
                else:
                    raise e
        return self._client
    
    def send_appointment_reminder(
        self,
        to_number: str,
        appointment_date: str,
        appointment_time: str,
        survey_id: str,
        call_id: str
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp appointment reminder using Twilio's Content API
        
        Args:
            to_number: WhatsApp number to send to (with or without whatsapp: prefix)
            appointment_date: Date of the appointment (replaces {{1}} in template)
            appointment_time: Time of the appointment (replaces {{2}} in template)
            survey_id: ID of the survey being sent
            call_id: ID of the call being made
            
        Returns:
            Dict: Result of the WhatsApp message sending operation
        """
        if self.debug_mode:
            return self._simulate_whatsapp_message(to_number, appointment_date, appointment_time, survey_id, call_id)
        
        try:
            # Ensure the phone number has the whatsapp: prefix
            if not to_number.startswith('whatsapp:'):
                to_number = f"whatsapp:{to_number}"
            
            # Log all parameters being used
            logger.info(f"📱 Sending WhatsApp appointment reminder to {to_number} for survey {survey_id}")
            logger.info(f"🔧 Using FROM number: {self.settings.TWILIO_WHATSAPP_FROM}")
            logger.info(f"🔧 Using Content SID: {self.settings.TWILIO_WHATSAPP_CONTENT_SID}")
            logger.info(f"🔧 Template variables - appointment_date: '{appointment_date}', appointment_time: '{appointment_time}'")
            
            # Prepare content variables for the template
            content_variables = {
                "1": appointment_date,
                "2": appointment_time
            }
            
            logger.info(f"🔧 Content variables JSON: {json.dumps(content_variables)}")
            
            # Verify client and account before sending
            try:
                account_info = self.client.api.accounts(self.settings.TWILIO_ACCOUNT_SID).fetch()
                logger.info(f"🔧 Account verification: Status={account_info.status}, Type={account_info.type}")
            except TwilioRestException as auth_error:
                logger.error(f"❌ Account verification failed before sending message: {auth_error.msg} (Code: {auth_error.code})")
                return {
                    'success': False,
                    'error': f"Twilio account verification failed: {auth_error.msg}",
                    'error_code': auth_error.code
                }
            
            message = self.client.messages.create(
                to=to_number,
                from_=self.settings.TWILIO_WHATSAPP_FROM,  # whatsapp:+14155238886
                content_sid=self.settings.TWILIO_WHATSAPP_CONTENT_SID,  # HXb5b62575e6e4ff6129ad7c8efe1f983e
                content_variables=json.dumps(content_variables)
            )
            
            result = {
                'success': True,
                'message_sid': message.sid,
                'status': message.status,
                'direction': message.direction,
                'created_at': message.date_created.isoformat() if message.date_created else None,
                'to': to_number,
                'from': self.settings.TWILIO_WHATSAPP_FROM,
                'content_sid': self.settings.TWILIO_WHATSAPP_CONTENT_SID,
                'appointment_date': appointment_date,
                'appointment_time': appointment_time
            }
            
            logger.info(f"✅ WhatsApp message sent successfully: {message.sid}")
            return result
            
        except TwilioRestException as e:
            logger.error(f"❌ Twilio WhatsApp error: {e.msg} (Code: {e.code})")
            logger.error(f"❌ Twilio error details: {getattr(e, 'details', 'No additional details')}")
            logger.error(f"❌ Twilio error more info: {getattr(e, 'more_info', 'No more info')}")
            return {
                'success': False,
                'error': f"Twilio WhatsApp error: {e.msg}",
                'error_code': e.code
            }
        except Exception as e:
            logger.error(f"❌ Unexpected WhatsApp error: {e}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }
    
    def send_custom_template_message(
        self,
        to_number: str,
        content_sid: str,
        content_variables: Dict[str, str],
        survey_id: str = None,
        call_id: str = None
    ) -> Dict[str, Any]:
        """
        Send a custom WhatsApp message using any pre-approved template
        
        Args:
            to_number: The WhatsApp number to send to
            content_sid: The Twilio Content SID for the template
            content_variables: Dictionary of variables to fill in the template
            survey_id: Optional survey ID for tracking
            call_id: Optional call ID for tracking
            
        Returns:
            Dict: Twilio API response data
        """
        if self.debug_mode:
            return self._simulate_custom_whatsapp_message(to_number, content_sid, content_variables, survey_id, call_id)
        
        try:
            # Ensure the phone number has the whatsapp: prefix
            if not to_number.startswith('whatsapp:'):
                to_number = f"whatsapp:{to_number}"
            
            logger.info(f"📱 Sending custom WhatsApp message to {to_number} with template {content_sid}")
            
            message = self.client.messages.create(
                to=to_number,
                from_=self.settings.TWILIO_WHATSAPP_FROM,
                content_sid=content_sid,
                content_variables=json.dumps(content_variables)
            )
            
            result = {
                'success': True,
                'message_sid': message.sid,
                'status': message.status,
                'direction': message.direction,
                'created_at': message.date_created.isoformat() if message.date_created else None,
                'to': to_number,
                'from': self.settings.TWILIO_WHATSAPP_FROM,
                'content_sid': content_sid,
                'content_variables': content_variables
            }
            
            logger.info(f"✅ Custom WhatsApp message sent successfully: {message.sid}")
            return result
            
        except TwilioRestException as e:
            logger.error(f"❌ Twilio WhatsApp error: {e.msg} (Code: {e.code})")
            return {
                'success': False,
                'error': f"Twilio WhatsApp error: {e.msg}",
                'error_code': e.code
            }
        except Exception as e:
            logger.error(f"❌ Unexpected WhatsApp error: {e}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }
    
    def _simulate_whatsapp_message(self, to_number: str, appointment_date: str, appointment_time: str, survey_id: str, call_id: str) -> Dict[str, Any]:
        """
        Simulate a WhatsApp message for debug mode
        """
        logger.info(f"🎭 SIMULATING WhatsApp appointment reminder to {to_number} for {appointment_date} at {appointment_time} (Debug Mode)")
        
        # Generate a fake message SID
        fake_message_sid = f"SM{uuid.uuid4().hex[:32]}"
        
        return {
            'success': True,
            'message_sid': fake_message_sid,
            'status': 'sent',
            'direction': 'outbound-api',
            'created_at': datetime.utcnow().isoformat(),
            'to': to_number,
            'from': 'whatsapp:+14155238886',
            'content_sid': 'HXb5b62575e6e4ff6129ad7c8efe1f983e',
            'appointment_date': appointment_date,
            'appointment_time': appointment_time,
            'debug_mode': True,
            'note': 'This is a simulated WhatsApp message for development purposes'
        }
    
    def _simulate_custom_whatsapp_message(self, to_number: str, content_sid: str, content_variables: Dict[str, str], survey_id: str, call_id: str) -> Dict[str, Any]:
        """
        Simulate a custom WhatsApp message for debug mode
        """
        logger.info(f"🎭 SIMULATING custom WhatsApp message to {to_number} with template {content_sid} (Debug Mode)")
        
        # Generate a fake message SID
        fake_message_sid = f"SM{uuid.uuid4().hex[:32]}"
        
        return {
            'success': True,
            'message_sid': fake_message_sid,
            'status': 'sent',
            'direction': 'outbound-api',
            'created_at': datetime.utcnow().isoformat(),
            'to': to_number,
            'from': 'whatsapp:+14155238886',
            'content_sid': content_sid,
            'content_variables': content_variables,
            'debug_mode': True,
            'note': 'This is a simulated custom WhatsApp message for development purposes'
        }
    
    def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Get the status of a WhatsApp message
        
        Args:
            message_sid: The Twilio message SID
            
        Returns:
            Dict: Message status information
        """
        if self.debug_mode and message_sid.startswith('SM'):
            return self._simulate_message_status(message_sid)
        
        try:
            message = self.client.messages(message_sid).fetch()
            
            return {
                'success': True,
                'message_sid': message.sid,
                'status': message.status,
                'direction': message.direction,
                'error_code': message.error_code,
                'error_message': message.error_message,
                'date_sent': message.date_sent.isoformat() if message.date_sent else None,
                'date_updated': message.date_updated.isoformat() if message.date_updated else None,
                'price': message.price
            }
            
        except TwilioRestException as e:
            logger.error(f"❌ Error getting message status: {e.msg}")
            return {
                'success': False,
                'error': f"Twilio error: {e.msg}",
                'error_code': e.code
            }
    
    def _simulate_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Simulate message status for debug mode
        """
        return {
            'success': True,
            'message_sid': message_sid,
            'status': 'delivered',
            'direction': 'outbound-api',
            'error_code': None,
            'error_message': None,
            'date_sent': datetime.utcnow().isoformat(),
            'date_updated': datetime.utcnow().isoformat(),
            'price': '-0.005',
            'debug_mode': True
        }

# Global instance
whatsapp_service = WhatsAppService() 