from typing import Dict, Any, List, Optional, Union, Callable
import json
import asyncio
from datetime import datetime

from ...core.config import get_settings
from ...core.logging import get_logger

logger = get_logger("services.llm.action_tools")
settings = get_settings()

class ActionTools:
    """
    Provides tools and functions that can be called by the LLM to take actions
    during phone surveys and conversations.
    """
    
    def __init__(self):
        """Initialize action tools"""
        self.tools = {
            "create_ticket": self.create_ticket,
            "lookup_information": self.lookup_information,
            "execute_sentiment_analysis": self.execute_sentiment_analysis,
            "transfer_to_agent": self.transfer_to_agent,
            "send_notification": self.send_notification,
            "get_customer_data": self.get_customer_data,
            "schedule_callback": self.schedule_callback
        }
    
    def get_tools_description(self) -> str:
        """
        Get a formatted description of available tools
        
        Returns:
            str: Description of available tools
        """
        description = "You have access to the following tools to assist during the conversation:\n\n"
        
        for name, func in self.tools.items():
            doc = func.__doc__ or "No description available"
            description += f"- {name}: {doc.strip().split('.')[0]}.\n"
        
        return description
    
    def get_available_tools(self) -> Dict[str, Callable]:
        """
        Get a dictionary of available tools
        
        Returns:
            Dict: Map of tool names to functions
        """
        return self.tools
    
    async def execute_tool(self, tool_name: str, **params) -> Dict[str, Any]:
        """
        Execute a tool by name with provided parameters
        
        Args:
            tool_name: Name of the tool to execute
            **params: Parameters to pass to the tool
        
        Returns:
            Dict: Tool execution result
        """
        if tool_name not in self.tools:
            return {
                "error": f"Tool '{tool_name}' not found",
                "available_tools": list(self.tools.keys())
            }
        
        try:
            tool_func = self.tools[tool_name]
            result = await tool_func(**params)
            return {
                "tool": tool_name,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}", exc_info=True)
            return {
                "tool": tool_name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def create_ticket(
        self, 
        title: str, 
        description: str, 
        priority: str = "medium",
        category: str = "general",
        contact_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a support or follow-up ticket based on customer feedback.
        
        Args:
            title: Ticket title
            description: Detailed description
            priority: Ticket priority (low, medium, high, urgent)
            category: Ticket category
            contact_info: Customer contact information
            
        Returns:
            Dict: Ticket creation result
        """
        # In a real implementation, this would integrate with a ticketing system
        # For now, we'll simulate ticket creation
        
        logger.info(f"Simulating ticket creation: {title}")
        
        # Generate a mock ticket ID
        import uuid
        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        
        return {
            "ticket_id": ticket_id,
            "title": title,
            "description": description,
            "priority": priority,
            "category": category,
            "created_at": datetime.utcnow().isoformat(),
            "status": "open"
        }
    
    async def lookup_information(
        self, 
        query: str,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Look up information from the knowledge base to answer customer questions.
        
        Args:
            query: Search query
            category: Optional category to narrow search
            
        Returns:
            Dict: Search results
        """
        # In a real implementation, this would query the vector database
        logger.info(f"Simulating knowledge base lookup: {query}")
        
        # Return mock results
        return {
            "query": query,
            "results": [
                {
                    "source": "Knowledge Base",
                    "content": "This is a simulated response to the query.",
                    "relevance_score": 0.92
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def execute_sentiment_analysis(
        self, 
        text: str
    ) -> Dict[str, Any]:
        """
        Perform sentiment analysis on customer response.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict: Sentiment analysis results
        """
        # In a real implementation, this would use a sentiment analysis service or model
        logger.info(f"Simulating sentiment analysis for text: {text[:50]}...")
        
        # Generate mock sentiment scores based on keywords
        positive_indicators = ["good", "great", "happy", "satisfied", "excellent", "thank", "appreciate"]
        negative_indicators = ["bad", "poor", "unhappy", "disappointed", "terrible", "issue", "problem"]
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_indicators if word in text_lower)
        negative_count = sum(1 for word in negative_indicators if word in text_lower)
        
        total = positive_count + negative_count
        
        if total == 0:
            sentiment_score = 0.0  # Neutral
        else:
            sentiment_score = (positive_count - negative_count) / (positive_count + negative_count)
            sentiment_score = max(-1.0, min(1.0, sentiment_score))  # Clamp to [-1, 1]
        
        # Determine sentiment category
        if sentiment_score >= 0.5:
            sentiment = "positive"
        elif sentiment_score >= 0.0:
            sentiment = "neutral"
        elif sentiment_score >= -0.5:
            sentiment = "slightly_negative"
        else:
            sentiment = "negative"
        
        return {
            "sentiment": sentiment,
            "score": sentiment_score,
            "confidence": 0.85,
            "analyzed_text": text[:100] + ("..." if len(text) > 100 else "")
        }
    
    async def transfer_to_agent(
        self, 
        reason: str,
        call_sid: Optional[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Transfer the call to a human agent when needed.
        
        Args:
            reason: Reason for transfer
            call_sid: Active call SID
            priority: Transfer priority
            
        Returns:
            Dict: Transfer result
        """
        # In a real implementation, this would initiate a call transfer
        logger.info(f"Simulating transfer to agent: {reason}")
        
        return {
            "transfer_id": f"TRF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "reason": reason,
            "call_sid": call_sid,
            "status": "queued",
            "estimated_wait_time": "3-5 minutes"
        }
    
    async def send_notification(
        self, 
        message: str,
        recipient_type: str = "user",
        recipient_id: Optional[str] = None,
        notification_type: str = "info"
    ) -> Dict[str, Any]:
        """
        Send a notification to the system or user.
        
        Args:
            message: Notification message
            recipient_type: Type of recipient (user, admin, system)
            recipient_id: Optional specific recipient ID
            notification_type: Notification type (info, warning, alert)
            
        Returns:
            Dict: Notification result
        """
        # In a real implementation, this would send a notification
        logger.info(f"Simulating notification: {message}")
        
        return {
            "notification_id": f"NOTIF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "message": message,
            "recipient_type": recipient_type,
            "recipient_id": recipient_id,
            "type": notification_type,
            "status": "sent",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_customer_data(
        self, 
        phone_number: str,
        data_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve customer data for personalization if available.
        
        Args:
            phone_number: Customer phone number
            data_type: Type of data to retrieve (profile, history, preferences)
            
        Returns:
            Dict: Customer data
        """
        # In a real implementation, this would query a CRM or database
        logger.info(f"Simulating customer data lookup for: {phone_number}")
        
        # Generate a sanitized phone number for the log
        sanitized = phone_number[-4:].rjust(len(phone_number), '*')
        
        # Return mock customer data
        return {
            "phone_number": sanitized,
            "found": True,
            "data": {
                "name": "Sample Customer",
                "customer_since": "2023-06-15",
                "segment": "Premium",
                "last_contact": "2025-03-10"
            }
        }
    
    async def schedule_callback(
        self, 
        phone_number: str,
        reason: str,
        preferred_time: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Schedule a callback for the customer at a later time.
        
        Args:
            phone_number: Customer phone number
            reason: Reason for callback
            preferred_time: Optional preferred callback time
            notes: Additional notes
            
        Returns:
            Dict: Callback scheduling result
        """
        # In a real implementation, this would create a scheduled call
        logger.info(f"Simulating callback scheduling for: {phone_number}")
        
        # Generate a sanitized phone number for the log
        sanitized = phone_number[-4:].rjust(len(phone_number), '*')
        
        return {
            "callback_id": f"CB-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "phone_number": sanitized,
            "reason": reason,
            "scheduled_time": preferred_time or "Next available time",
            "status": "scheduled"
        }