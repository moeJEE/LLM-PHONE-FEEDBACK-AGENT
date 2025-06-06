from typing import Dict, Any, List, Optional, Union
import os
import re
import json
import asyncio
from datetime import datetime
from enum import Enum

from ...core.config import get_settings
from ...core.logging import get_logger
from ..llm.cot_engine import CoTEngine

logger = get_logger("services.sentiment.analyzer")
settings = get_settings()

class SentimentCategory(str, Enum):
    """Enumeration of sentiment categories"""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"
    MIXED = "mixed"

class SentimentAnalyzer:
    """
    Service for analyzing sentiment in text, particularly customer feedback and survey responses.
    Can use either a direct API-based sentiment analyzer or LLM-based analysis.
    """
    
    def __init__(self):
        """Initialize sentiment analyzer"""
        self.llm_engine = CoTEngine()
    
    async def analyze_text(
        self, 
        text: str,
        context: Optional[str] = None,
        categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment in a text passage
        
        Args:
            text: Text to analyze
            context: Optional context to help with sentiment analysis
            categories: Optional specific categories to classify sentiment into
            
        Returns:
            Dict: Sentiment analysis results
        """
        try:
            # Use the LLM-based sentiment analyzer
            return await self._analyze_with_llm(text, context, categories)
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "sentiment": SentimentCategory.NEUTRAL,
                "score": 0.0,
                "confidence": 0.0
            }
    
    async def analyze_survey_response(
        self, 
        response: str,
        question: Dict[str, Any],
        survey_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment in a survey response with additional context
        
        Args:
            response: The customer's response text
            question: The question that was asked
            survey_context: Additional context about the survey
            
        Returns:
            Dict: Sentiment analysis results with additional insights
        """
        try:
            # Prepare context for analysis
            context = f"Question: {question.get('text', '')}\n"
            if survey_context:
                context += f"Survey: {survey_context.get('title', '')}\n"
                context += f"Purpose: {survey_context.get('description', '')}\n"
            
            # Analyze the sentiment
            sentiment_result = await self._analyze_with_llm(response, context)
            
            # Extract more detailed insights based on the question type
            question_type = question.get('question_type', 'open_ended')
            
            if question_type == 'numeric':
                # For numeric ratings, map to sentiment categories
                try:
                    rating = int(response.strip())
                    if rating <= 2:
                        sentiment_result['sentiment'] = SentimentCategory.NEGATIVE
                        sentiment_result['score'] = -0.5
                    elif rating == 3:
                        sentiment_result['sentiment'] = SentimentCategory.NEUTRAL
                        sentiment_result['score'] = 0.0
                    else:  # 4-5
                        sentiment_result['sentiment'] = SentimentCategory.POSITIVE
                        sentiment_result['score'] = 0.5
                except ValueError:
                    # If we can't parse as a number, stick with LLM analysis
                    pass
            
            # Add additional insights
            additional_insights = await self._extract_insights(response, question, sentiment_result)
            sentiment_result.update(additional_insights)
            
            return sentiment_result
            
        except Exception as e:
            logger.error(f"Error analyzing survey response: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "sentiment": SentimentCategory.NEUTRAL,
                "score": 0.0,
                "confidence": 0.0
            }
    
    async def analyze_conversation(
        self, 
        conversation: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze sentiment in a complete conversation
        
        Args:
            conversation: List of conversation turns with speaker and text
            
        Returns:
            Dict: Overall sentiment analysis and turn-by-turn breakdown
        """
        try:
            # First, concatenate all customer messages
            customer_text = ""
            for turn in conversation:
                if not turn.get("is_ai", False):
                    customer_text += turn.get("text", "") + " "
            
            # Analyze overall sentiment
            overall_sentiment = await self._analyze_with_llm(customer_text)
            
            # Analyze each turn individually
            turn_analysis = []
            for turn in conversation:
                if not turn.get("is_ai", False):  # Only analyze customer messages
                    turn_sentiment = await self._analyze_with_llm(turn.get("text", ""))
                    turn_analysis.append({
                        "text": turn.get("text", ""),
                        "timestamp": turn.get("timestamp"),
                        "sentiment": turn_sentiment.get("sentiment"),
                        "score": turn_sentiment.get("score")
                    })
            
            # Extract key topics and themes
            topics = await self._extract_topics(customer_text)
            
            return {
                "success": True,
                "overall_sentiment": overall_sentiment.get("sentiment"),
                "overall_score": overall_sentiment.get("score"),
                "confidence": overall_sentiment.get("confidence"),
                "turn_by_turn": turn_analysis,
                "topics": topics,
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing conversation: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "overall_sentiment": SentimentCategory.NEUTRAL,
                "overall_score": 0.0
            }
    
    async def _analyze_with_llm(
        self, 
        text: str,
        context: Optional[str] = None,
        categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment using LLM with improved speed and error handling
        """
        # Quick sentiment analysis for very short texts
        if len(text.strip()) < 5:
            return {
                "success": True,
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "themes": [],
                "nuances": "Text too short for analysis"
            }
        
        try:
            # Simplified prompt for faster analysis
            limited_text = text[:100]  # Limit context length
            
            schema = """
{
  "sentiment": "positive|negative|neutral",
  "score": -1.0 to 1.0,
  "confidence": 0.0 to 1.0,
  "themes": ["theme1", "theme2"],
  "nuances": "brief description"
}"""
            
            result = await self.llm_engine.generate_structured_output(
                limited_text,
                schema
            )
            
            # Ensure result has correct format
            if isinstance(result, dict) and result.get('success', True):
                # Normalize sentiment value
                sentiment = result.get('sentiment', 'neutral')
                if isinstance(sentiment, str):
                    sentiment = sentiment.lower()
                
                return {
                    "success": True,
                    "sentiment": sentiment,
                    "score": float(result.get('score', 0.0)),
                    "confidence": float(result.get('confidence', 0.5)),
                    "themes": result.get('themes', []),
                    "nuances": result.get('nuances', 'No additional details')
                }
            else:
                return self._quick_sentiment_fallback(text)
                
        except Exception as e:
            logger.error(f"Error in LLM sentiment analysis: {e}")
            return self._quick_sentiment_fallback(text)
    
    def _quick_sentiment_fallback(self, text):
        """
        Quick keyword-based sentiment analysis as fallback
        """
        try:
            text_lower = text.lower() if isinstance(text, str) else str(text).lower()
            
            # Simple keyword lists
            positive_words = ['good', 'great', 'love', 'like', 'amazing', 'excellent', 'perfect', 'awesome', 'nice', 'happy']
            negative_words = ['bad', 'hate', 'terrible', 'awful', 'worst', 'horrible', 'frustrating', 'annoying', 'poor', 'sad']
            
            # Count occurrences
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            # Determine sentiment
            if positive_count > negative_count:
                sentiment = "positive"
                score = min(0.8, 0.3 + positive_count * 0.1)
            elif negative_count > positive_count:
                sentiment = "negative"  
                score = max(-0.8, -0.3 - negative_count * 0.1)
            else:
                sentiment = "neutral"
                score = 0.0
                
            return {
                "success": True,
                "sentiment": sentiment,
                "score": score,
                "confidence": 0.6,
                "themes": ["keyword_analysis"],
                "nuances": f"Based on keyword analysis: {positive_count} positive, {negative_count} negative words"
            }
            
        except Exception as e:
            logger.error(f"Error in fallback sentiment analysis: {e}")
            return {
                "success": False,
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "themes": [],
                "nuances": "Analysis failed"
            }
    
    async def _extract_insights(
        self, 
        response: str, 
        question: Dict[str, Any],
        sentiment_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract additional insights from the response based on question type"""
        # Build prompt for extracting insights
        question_type = question.get('question_type', 'open_ended')
        
        prompt = f"""
Based on this customer response to a survey question:

Question: {question.get('text', '')}
Response: {response}
Question Type: {question_type}
Detected Sentiment: {sentiment_result.get('sentiment')}

Extract the following insights:
1. Key points or main takeaways
2. Action items or suggestions (if any)
3. Specific products, services, or features mentioned (if any)
4. Level of satisfaction or dissatisfaction
5. Whether a follow-up is recommended

Provide your answer as a JSON object with the following fields:
- key_points: array of main points
- action_items: array of suggested actions
- mentioned_items: array of specific products/services/features
- satisfaction_level: string (very satisfied, satisfied, neutral, dissatisfied, very dissatisfied)
- follow_up_recommended: boolean
"""

        try:
            insights = await self.llm_engine.generate_structured_output(
                prompt,
                {
                    "type": "object",
                    "properties": {
                        "key_points": {"type": "array", "items": {"type": "string"}},
                        "action_items": {"type": "array", "items": {"type": "string"}},
                        "mentioned_items": {"type": "array", "items": {"type": "string"}},
                        "satisfaction_level": {"type": "string"},
                        "follow_up_recommended": {"type": "boolean"}
                    }
                }
            )
            
            return {
                "insights": insights
            }
            
        except Exception as e:
            logger.error(f"Error extracting insights: {str(e)}", exc_info=True)
            return {
                "insights": {
                    "key_points": [],
                    "action_items": [],
                    "mentioned_items": [],
                    "satisfaction_level": "neutral",
                    "follow_up_recommended": False
                }
            }
    
    async def _extract_topics(self, text: str) -> List[Dict[str, Any]]:
        """Extract key topics and themes from text"""
        prompt = f"""
Extract the main topics and themes from the following customer text:

{text}

For each topic:
1. Provide a short name or label
2. Rate its importance/prominence in the text (high, medium, low)
3. Note whether it's discussed positively, negatively, or neutrally
4. Provide a brief explanation of why this is a key topic

Return as a JSON array where each object has:
- topic: the topic name
- importance: importance level
- sentiment: positive, negative, or neutral
- explanation: brief explanation
"""

        try:
            topics = await self.llm_engine.generate_structured_output(
                prompt,
                {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string"},
                            "importance": {"type": "string"},
                            "sentiment": {"type": "string"},
                            "explanation": {"type": "string"}
                        }
                    }
                }
            )
            
            return topics
            
        except Exception as e:
            logger.error(f"Error extracting topics: {str(e)}", exc_info=True)
            return []