"""
Twilio service for making and managing phone calls
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class TwilioService:
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self.debug_mode = self.settings.DEBUG
        
    @property
    def client(self) -> Client:
        if self._client is None:
            try:
                self._client = Client(
                    self.settings.TWILIO_ACCOUNT_SID,
                    self.settings.TWILIO_AUTH_TOKEN
                )
                # Test the connection
                if not self.debug_mode:
                    self._client.api.accounts(self.settings.TWILIO_ACCOUNT_SID).fetch()
                    logger.info("✅ Twilio client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Twilio client: {e}")
                if self.debug_mode:
                    logger.warning("🔧 Running in DEBUG mode - Twilio calls will be simulated")
                else:
                    raise e
        return self._client
    
    def make_call(
        self,
        to_number: str,
        survey_id: str,
        call_id: str,
        webhook_url: str,
        status_callback_url: str
    ) -> Dict[str, Any]:
        """
        Make a phone call via Twilio
        """
        if self.debug_mode:
            return self._simulate_call(to_number, survey_id, call_id)
        
        try:
            logger.info(f"📞 Making call to {to_number} for survey {survey_id}")
            
            call = self.client.calls.create(
                to=to_number,
                from_=self.settings.TWILIO_PHONE_NUMBER,
                url=webhook_url,
                status_callback=status_callback_url,
                status_callback_event=['initiated', 'ringing', 'answered', 'completed', 'failed'],
                record=True,
                recording_status_callback=self.settings.TWILIO_RECORDING_CALLBACK_URL
            )
            
            result = {
                'success': True,
                'call_sid': call.sid,
                'status': call.status,
                'direction': call.direction,
                'created_at': call.date_created.isoformat() if call.date_created else None
            }
            
            logger.info(f"✅ Call created successfully: {call.sid}")
            return result
            
        except TwilioRestException as e:
            logger.error(f"❌ Twilio error making call: {e.msg} (Code: {e.code})")
            return {
                'success': False,
                'error': f"Twilio error: {e.msg}",
                'error_code': e.code
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error making call: {e}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }
    
    def _simulate_call(self, to_number: str, survey_id: str, call_id: str) -> Dict[str, Any]:
        """
        Simulate a Twilio call for debug mode
        """
        logger.info(f"🎭 SIMULATING call to {to_number} for survey {survey_id} (Debug Mode)")
        
        # Generate a fake call SID
        fake_call_sid = f"CA{uuid.uuid4().hex[:32]}"
        
        return {
            'success': True,
            'call_sid': fake_call_sid,
            'status': 'initiated',
            'direction': 'outbound-api',
            'created_at': datetime.utcnow().isoformat(),
            'debug_mode': True,
            'note': 'This is a simulated call for development purposes'
        }
    
    def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """
        Get the status of a call
        """
        if self.debug_mode and call_sid.startswith('CA'):
            return self._simulate_call_status(call_sid)
        
        try:
            call = self.client.calls(call_sid).fetch()
            
            return {
                'success': True,
                'call_sid': call.sid,
                'status': call.status,
                'direction': call.direction,
                'duration': call.duration,
                'start_time': call.start_time.isoformat() if call.start_time else None,
                'end_time': call.end_time.isoformat() if call.end_time else None,
                'price': call.price
            }
            
        except TwilioRestException as e:
            logger.error(f"❌ Error getting call status: {e.msg}")
            return {
                'success': False,
                'error': f"Twilio error: {e.msg}",
                'error_code': e.code
            }
    
    def _simulate_call_status(self, call_sid: str) -> Dict[str, Any]:
        """
        Simulate call status for debug mode
        """
        return {
            'success': True,
            'call_sid': call_sid,
            'status': 'completed',
            'direction': 'outbound-api',
            'duration': '30',
            'start_time': datetime.utcnow().isoformat(),
            'end_time': datetime.utcnow().isoformat(),
            'price': '-0.0075',
            'debug_mode': True
        }
    
    def end_call(self, call_sid: str) -> Dict[str, Any]:
        """
        End/hang up a call
        """
        if self.debug_mode and call_sid.startswith('CA'):
            logger.info(f"🎭 SIMULATING call end for {call_sid} (Debug Mode)")
            return {
                'success': True,
                'call_sid': call_sid,
                'status': 'completed',
                'debug_mode': True
            }
        
        try:
            call = self.client.calls(call_sid).update(status='completed')
            
            logger.info(f"✅ Call {call_sid} ended successfully")
            return {
                'success': True,
                'call_sid': call.sid,
                'status': call.status
            }
            
        except TwilioRestException as e:
            logger.error(f"❌ Error ending call: {e.msg}")
            return {
                'success': False,
                'error': f"Twilio error: {e.msg}",
                'error_code': e.code
            }

# Global instance
twilio_service = TwilioService() 