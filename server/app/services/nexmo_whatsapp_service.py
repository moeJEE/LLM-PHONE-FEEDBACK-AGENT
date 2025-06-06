"""
Nexmo/Vonage WhatsApp service for sending business-initiated messages
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
import json
import base64
import hmac
import hashlib
import requests
import os

import vonage
from vonage import VonageError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class VonageWhatsAppError(Exception):
    """Custom exception for Vonage WhatsApp service errors"""
    pass


class NexmoWhatsAppService:
    def __init__(self):
        self.settings = get_settings()
        self._messages_client = None
        self._account_client = None
        self.simulation_mode = self.settings.WHATSAPP_SIMULATION_MODE
        
    @property
    def messages_client(self) -> vonage.Messages:
        if self._messages_client is None:
            try:
                # Log credentials being used (first few characters only for security)
                logger.info(f"🔧 Initializing Nexmo Messages client with API Key: {self.settings.NEXMO_API_KEY[:8]}...")
                logger.info(f"🔧 API Secret starts with: {self.settings.NEXMO_API_SECRET[:8]}...")
                
                # Create auth and Vonage client, then extract HTTP client for Messages
                auth = vonage.Auth(
                    api_key=self.settings.NEXMO_API_KEY,
                    api_secret=self.settings.NEXMO_API_SECRET
                )
                vonage_client = vonage.Vonage(auth)
                self._messages_client = vonage.Messages(vonage_client._http_client)
                
                logger.info("✅ Nexmo Messages client initialized successfully")
                    
            except Exception as e:
                logger.error(f"❌ Failed to initialize Nexmo Messages client: {e}")
                raise e
        return self._messages_client
    
    @property
    def account_client(self) -> vonage.Account:
        if self._account_client is None:
            try:
                # Create auth and Vonage client, then extract HTTP client for Account
                auth = vonage.Auth(
                    api_key=self.settings.NEXMO_API_KEY,
                    api_secret=self.settings.NEXMO_API_SECRET
                )
                vonage_client = vonage.Vonage(auth)
                self._account_client = vonage.Account(vonage_client._http_client)
                
                # Test the connection in production mode
                if not self.simulation_mode:
                    try:
                        # Test with a simple account balance check
                        account = self._account_client.get_balance()
                        logger.info(f"✅ Nexmo account verified. Balance: {account['value']} {account['currency']}")
                    except VonageError as e:
                        logger.error(f"❌ Nexmo account verification failed: {e}")
                        raise e
                else:
                    logger.info("✅ Nexmo account client initialized (SIMULATION MODE)")
                    
            except Exception as e:
                logger.error(f"❌ Failed to initialize Nexmo Account client: {e}")
                raise e
        return self._account_client
    
    async def send_whatsapp_message(self, to: str, message: str) -> Dict[str, Any]:
        """Send a WhatsApp message"""
        # Normalize phone number - remove + prefix and any non-digits
        normalized_to = to.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        logger.info(f"📱 Sending WhatsApp message to {normalized_to} (original: {to})")
        
        if self.simulation_mode:
            message_uuid = f"sim_{uuid.uuid4()}"
            logger.info(f"🎭 SIMULATION: WhatsApp message sent to {normalized_to}: {message[:50]}...")
            return {
                'success': True,
                'message_uuid': message_uuid,
                'to': normalized_to,
                'from': self.settings.NEXMO_WHATSAPP_FROM,
                'timestamp': datetime.utcnow().isoformat(),
                'simulation_mode': True
            }
        
        try:
            # Use environment variable for API URL
            api_url = os.getenv("NEXMO_MESSAGES_API_URL", "https://messages-sandbox.nexmo.com/v1/messages")
            
            headers = {
                "Authorization": f"Bearer {self.jwt}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            message_data = {
                "from": self.settings.NEXMO_WHATSAPP_FROM,
                "to": normalized_to,
                "message_type": "text",
                "text": message,
                "channel": "whatsapp"
            }
            
            logger.info(f"📤 Sending message data: {message_data}")
            logger.info(f"🔑 Using API Key: {self.settings.NEXMO_API_KEY}")
            logger.info(f"🔑 Using API Secret: {self.settings.NEXMO_API_SECRET[:8]}...")
            logger.info(f"📞 Using From Number: {self.settings.NEXMO_WHATSAPP_FROM}")
            
            response = requests.post(api_url, json=message_data, headers=headers)
            
            if response.status_code in [200, 202]:
                response_data = response.json()
                message_uuid = response_data.get('message_uuid')
                logger.info(f"✅ WhatsApp message sent successfully. UUID: {message_uuid}")
                return {
                    'success': True,
                    'message_uuid': message_uuid,
                    'to': normalized_to,
                    'from': self.settings.NEXMO_WHATSAPP_FROM,
                    'timestamp': datetime.utcnow().isoformat()
                }
            elif response.status_code == 403:
                # Handle whitelist error specifically
                try:
                    error_data = response.json()
                    if "whitelisted" in error_data.get('title', '').lower():
                        error_msg = f"Phone number {normalized_to} is not whitelisted for WhatsApp sandbox. Please add it to your Nexmo dashboard whitelist or contact support to enable production WhatsApp API."
                    else:
                        error_msg = f"HTTP 403 Forbidden: {error_data.get('title', response.text)}"
                except:
                    error_msg = f"HTTP 403 Forbidden: {response.text}"
                logger.error(f"❌ WhatsApp whitelist error: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'error_code': 'WHITELIST_REQUIRED',
                    'to': normalized_to,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"❌ API request failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'to': normalized_to,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            logger.error(f"❌ Unexpected error sending WhatsApp message: {e}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'to': normalized_to,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def send_template_message(
        self,
        to_number: str,
        template_name: str,
        template_parameters: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp template message
        
        Args:
            to_number: The WhatsApp number to send to (can include + prefix)
            template_name: The name of the template
            template_parameters: Optional template parameters
            
        Returns:
            Dict: Nexmo API response data
        """
        if self.simulation_mode:
            return self._simulate_template_message(to_number, template_name, template_parameters)
        
        try:
            # Normalize phone number - remove + prefix and any non-digits
            normalized_to = to_number.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            
            logger.info(f"📋 Sending WhatsApp template message to {normalized_to} (original: {to_number}) with template {template_name}")
            
            message_data = {
                "from": self.settings.NEXMO_WHATSAPP_FROM,
                "to": normalized_to,
                "message_type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en"}
                },
                "channel": "whatsapp"
            }
            
            # Add parameters if provided
            if template_parameters:
                message_data["template"]["parameters"] = [
                    {"type": "text", "text": value} for value in template_parameters.values()
                ]
            
            response = self.messages_client.send(message_data)
            
            result = {
                'success': True,
                'message_uuid': response['message_uuid'],
                'to': normalized_to,
                'from': self.settings.NEXMO_WHATSAPP_FROM,
                'template_name': template_name,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ WhatsApp template message sent successfully: {response['message_uuid']}")
            return result
            
        except VonageError as e:
            logger.error(f"❌ Nexmo WhatsApp template error: {e}")
            return {
                'success': False,
                'error': f"Nexmo WhatsApp error: {str(e)}",
                'error_code': getattr(e, 'code', 'UNKNOWN')
            }
        except Exception as e:
            logger.error(f"❌ Unexpected WhatsApp template error: {e}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }
    
    async def send_appointment_reminder(
        self,
        to_number: str,
        appointment_date: str,
        appointment_time: str,
        survey_id: str = None,
        call_id: str = None
    ) -> Dict[str, Any]:
        """
        Send an appointment reminder WhatsApp message
        
        Args:
            to_number: The WhatsApp number to send to
            appointment_date: The appointment date
            appointment_time: The appointment time
            survey_id: Optional survey ID for tracking
            call_id: Optional call ID for tracking
            
        Returns:
            Dict: Nexmo API response data
        """
        message_text = f"🗓️ Appointment Reminder\n\nHello! This is a reminder about your upcoming appointment:\n\n📅 Date: {appointment_date}\n🕐 Time: {appointment_time}\n\nWe look forward to speaking with you. If you need to reschedule, please let us know.\n\nThank you!"
        
        try:
            whatsapp_result = await self.send_whatsapp_message(to_number, message_text)
            
            if whatsapp_result.get('success'):
                result = {
                    'success': True,
                    'message_uuid': whatsapp_result.get('message_uuid'),
                    'to': to_number,
                    'appointment_date': appointment_date,
                    'appointment_time': appointment_time,
                    'survey_id': survey_id,
                    'call_id': call_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                return result
            else:
                return {
                    'success': False,
                    'error': whatsapp_result.get('error', 'Failed to send WhatsApp message'),
                    'to': to_number,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'to': to_number,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_message_status(self, message_uuid: str) -> Dict[str, Any]:
        """
        Get the status of a WhatsApp message
        
        Args:
            message_uuid: The Nexmo message UUID
            
        Returns:
            Dict: Message status information
        """
        if self.simulation_mode and message_uuid.startswith('test_'):
            return self._simulate_message_status(message_uuid)
        
        try:
            # Note: Nexmo doesn't have a direct get message status API
            # Status updates come via webhooks
            return {
                'success': True,
                'message_uuid': message_uuid,
                'status': 'sent',
                'note': 'Status tracking via webhooks. Check webhook logs for delivery status.'
            }
            
        except VonageError as e:
            logger.error(f"❌ Error getting message status: {e}")
            return {
                'success': False,
                'error': f"Nexmo error: {str(e)}",
                'error_code': getattr(e, 'code', 'UNKNOWN')
            }
    
    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """
        Verify Nexmo webhook signature
        
        Args:
            body: Raw request body
            signature: Signature from X-Nexmo-Signature header
            
        Returns:
            bool: Whether the signature is valid
        """
        if self.simulation_mode:
            logger.info("🎭 SIMULATING webhook signature validation (SIMULATION MODE)")
            return True
        
        try:
            # Create HMAC signature
            expected_signature = hmac.new(
                self.settings.NEXMO_API_SECRET.encode('utf-8'),
                body,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"❌ Error verifying webhook signature: {e}")
            return False
    
    def _simulate_whatsapp_message(self, to_number: str, text: str) -> Dict[str, Any]:
        """
        Simulate sending a WhatsApp message for debug mode
        """
        message_uuid = f"test_{uuid.uuid4().hex[:16]}"
        logger.info(f"🎭 SIMULATING WhatsApp message to {to_number}: {text[:50]}...")
        
        return {
            'success': True,
            'message_uuid': message_uuid,
            'to': to_number,
            'from': self.settings.NEXMO_WHATSAPP_FROM,
            'timestamp': datetime.utcnow().isoformat(),
            'debug_mode': True
        }
    
    def _simulate_template_message(self, to_number: str, template_name: str, template_parameters: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Simulate sending a template message for debug mode
        """
        message_uuid = f"test_{uuid.uuid4().hex[:16]}"
        logger.info(f"🎭 SIMULATING WhatsApp template message to {to_number} with template {template_name}")
        
        return {
            'success': True,
            'message_uuid': message_uuid,
            'to': to_number,
            'from': self.settings.NEXMO_WHATSAPP_FROM,
            'template_name': template_name,
            'timestamp': datetime.utcnow().isoformat(),
            'debug_mode': True
        }
    
    def _simulate_message_status(self, message_uuid: str) -> Dict[str, Any]:
        """
        Simulate message status for debug mode
        """
        return {
            'success': True,
            'message_uuid': message_uuid,
            'status': 'delivered',
            'timestamp': datetime.utcnow().isoformat(),
            'debug_mode': True
        } 