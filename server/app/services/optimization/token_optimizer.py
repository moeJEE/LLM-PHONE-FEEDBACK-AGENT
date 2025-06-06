"""
Token Optimization Service for OpenAI API Cost Reduction
"""
import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
import asyncio

from ...db.mongodb import MongoDB

logger = logging.getLogger(__name__)

class PromptType(str, Enum):
    SURVEY_GENERATION = "survey_generation"
    FOLLOW_UP_GENERATION = "follow_up_generation"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    SUMMARY_GENERATION = "summary_generation"
    QUESTION_GENERATION = "question_generation"
    KNOWLEDGE_BASE_RESPONSE = "knowledge_base_response"
    RESPONSE_ANALYSIS = "response_analysis"
    FOLLOW_UP = "follow_up"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    BATCH_SENTIMENT_ANALYSIS = "batch_sentiment_analysis"

@dataclass
class TokenBudget:
    daily_limit: int = 50000
    monthly_limit: int = 1000000
    per_request_limit: int = 4000
    alert_threshold: float = 0.8
    cost_per_1k_tokens: float = 0.002

@dataclass
class TokenUsageRecord:
    timestamp: datetime
    prompt_type: PromptType
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    user_id: str
    optimization_applied: bool = False

class TokenOptimizer:
    def __init__(self, budget: TokenBudget = None):
        self.budget = budget or TokenBudget()
        self.optimization_cache = {}
        
    async def optimize_prompt(self, prompt: str, prompt_type: PromptType, context: Dict = None) -> str:
        """Optimize a prompt to reduce token consumption"""
        try:
            # Simple optimization strategies
            optimized = prompt
            
            # Remove redundant whitespace
            optimized = ' '.join(optimized.split())
            
            # Apply template optimization for common prompt types
            if prompt_type == PromptType.QUESTION_GENERATION:
                optimized = self._optimize_question_prompt(optimized)
            elif prompt_type == PromptType.RESPONSE_ANALYSIS:
                optimized = self._optimize_analysis_prompt(optimized)
            
            # Cache the optimization
            cache_key = hashlib.md5(prompt.encode()).hexdigest()
            self.optimization_cache[cache_key] = optimized
            
            return optimized
            
        except Exception as e:
            logger.error(f"Error optimizing prompt: {e}")
            return prompt
    
    def _optimize_question_prompt(self, prompt: str) -> str:
        """Optimize question generation prompts"""
        # Replace verbose instructions with concise ones
        replacements = {
            "Please generate a question that": "Generate a question that",
            "Could you please": "Please",
            "I would like you to": "",
            "Based on the information provided": "Based on:",
        }
        
        for old, new in replacements.items():
            prompt = prompt.replace(old, new)
        
        return prompt.strip()
    
    def _optimize_analysis_prompt(self, prompt: str) -> str:
        """Optimize analysis prompts"""
        # Use shorter analysis instructions
        replacements = {
            "Analyze the following response and provide": "Analyze and provide",
            "Please provide a detailed analysis": "Analyze",
            "sentiment analysis": "sentiment",
            "comprehensive": "",
        }
        
        for old, new in replacements.items():
            prompt = prompt.replace(old, new)
        
        return prompt.strip()
    
    async def check_budget(self, estimated_tokens: int, user_id: str) -> Dict[str, Any]:
        """Check if request is within budget limits"""
        try:
            collection = MongoDB.get_collection("token_usage")
            now = datetime.utcnow()
            
            # Check daily usage
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            daily_usage = await collection.aggregate([
                {"$match": {
                    "user_id": user_id,
                    "timestamp": {"$gte": start_of_day}
                }},
                {"$group": {"_id": None, "total": {"$sum": "$total_tokens"}}}
            ]).to_list(length=1)
            
            daily_total = daily_usage[0]["total"] if daily_usage else 0
            
            # Check monthly usage
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_usage = await collection.aggregate([
                {"$match": {
                    "user_id": user_id,
                    "timestamp": {"$gte": start_of_month}
                }},
                {"$group": {"_id": None, "total": {"$sum": "$total_tokens"}}}
            ]).to_list(length=1)
            
            monthly_total = monthly_usage[0]["total"] if monthly_usage else 0
            
            return {
                "within_budget": (
                    daily_total + estimated_tokens <= self.budget.daily_limit and
                    monthly_total + estimated_tokens <= self.budget.monthly_limit and
                    estimated_tokens <= self.budget.per_request_limit
                ),
                "daily_usage": daily_total,
                "monthly_usage": monthly_total,
                "daily_remaining": max(0, self.budget.daily_limit - daily_total),
                "monthly_remaining": max(0, self.budget.monthly_limit - monthly_total),
                "cost_estimate": (estimated_tokens / 1000) * self.budget.cost_per_1k_tokens
            }
            
        except Exception as e:
            logger.error(f"Error checking budget: {e}")
            return {"within_budget": True, "error": str(e)}
    
    async def record_usage(self, usage_record: TokenUsageRecord) -> None:
        """Record token usage in MongoDB"""
        try:
            collection = MongoDB.get_collection("token_usage")
            await collection.insert_one({
                "timestamp": usage_record.timestamp,
                "prompt_type": usage_record.prompt_type.value,
                "input_tokens": usage_record.input_tokens,
                "output_tokens": usage_record.output_tokens,
                "total_tokens": usage_record.total_tokens,
                "cost": usage_record.cost,
                "user_id": usage_record.user_id,
                "optimization_applied": usage_record.optimization_applied
            })
            
        except Exception as e:
            logger.error(f"Error recording usage: {e}")
    
    async def get_usage_analytics(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get comprehensive usage analytics"""
        try:
            collection = MongoDB.get_collection("token_usage")
            start_date = datetime.utcnow() - timedelta(days=days)
            
            usage_data = await collection.find({
                "user_id": user_id,
                "timestamp": {"$gte": start_date}
            }).to_list(length=None)
            
        except Exception as e:
            logger.error(f"Error fetching usage data: {e}")
            usage_data = []
        
        try:
            # If we have real data, use it
            if usage_data:
                logger.info(f"Using {len(usage_data)} real usage records for analytics")
                
                total_tokens = sum(record["total_tokens"] for record in usage_data)
                total_cost = sum(record["cost"] for record in usage_data)
                
                # Daily breakdown
                daily_usage = {}
                for record in usage_data:
                    date_key = record["timestamp"].strftime("%Y-%m-%d")
                    if date_key not in daily_usage:
                        daily_usage[date_key] = {"tokens": 0, "cost": 0}
                    daily_usage[date_key]["tokens"] += record["total_tokens"]
                    daily_usage[date_key]["cost"] += record["cost"]
                
                # Prompt type breakdown
                prompt_type_usage = {}
                for record in usage_data:
                    prompt_type = record["prompt_type"]
                    if prompt_type not in prompt_type_usage:
                        prompt_type_usage[prompt_type] = {"tokens": 0, "cost": 0, "requests": 0}
                    prompt_type_usage[prompt_type]["tokens"] += record["total_tokens"]
                    prompt_type_usage[prompt_type]["cost"] += record["cost"]
                    prompt_type_usage[prompt_type]["requests"] += 1
                
                # Calculate cache hit rate from real data
                cached_requests = sum(1 for record in usage_data if record.get("optimization_applied", False))
                cache_hit_rate = cached_requests / len(usage_data) if usage_data else 0.0
                
                return {
                    "total_tokens": total_tokens,
                    "total_cost": round(total_cost, 4),
                    "total_requests": len(usage_data),
                    "daily_breakdown": daily_usage,
                    "type_breakdown": prompt_type_usage,
                    "cache_hit_rate": cache_hit_rate,
                    "cached_requests": cached_requests,
                    "optimization_savings": sum(
                        record.get("tokens_saved", 0) for record in usage_data
                    ),
                    "data_source": "real"
                }
            
            # If no real data exists, provide sample data for demonstration
            else:
                logger.info("No real usage data found, using sample data for demonstration")
                today = datetime.utcnow()
                
                return {
                    "total_tokens": 15420,
                    "total_cost": 0.32,
                    "total_requests": 42,
                    "daily_breakdown": {
                        (today - timedelta(days=6)).strftime("%Y-%m-%d"): {"tokens": 1200, "cost": 0.024},
                        (today - timedelta(days=5)).strftime("%Y-%m-%d"): {"tokens": 2800, "cost": 0.056},
                        (today - timedelta(days=4)).strftime("%Y-%m-%d"): {"tokens": 1950, "cost": 0.039},
                        (today - timedelta(days=3)).strftime("%Y-%m-%d"): {"tokens": 3100, "cost": 0.062},
                        (today - timedelta(days=2)).strftime("%Y-%m-%d"): {"tokens": 2470, "cost": 0.049},
                        (today - timedelta(days=1)).strftime("%Y-%m-%d"): {"tokens": 2180, "cost": 0.044},
                        today.strftime("%Y-%m-%d"): {"tokens": 1720, "cost": 0.034}
                    },
                    "type_breakdown": {
                        "survey_generation": {"tokens": 5200, "cost": 0.104, "requests": 15},
                        "sentiment_analysis": {"tokens": 4800, "cost": 0.096, "requests": 12},
                        "knowledge_retrieval": {"tokens": 3220, "cost": 0.064, "requests": 8},
                        "batch_sentiment_analysis": {"tokens": 2200, "cost": 0.044, "requests": 7}
                    },
                    "cache_hit_rate": 0.35,
                    "cached_requests": 0,
                    "optimization_savings": 2800,
                    "data_source": "sample"
                }
            
        except Exception as e:
            logger.error(f"Error getting usage analytics: {e}")
            return {"error": str(e)}
    
    def estimate_tokens(self, text: str) -> int:
        """Simple token estimation (rough approximation)"""
        # Rough estimation: ~4 characters per token
        return max(1, len(text) // 4)
    
    async def get_optimization_insights(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate optimization recommendations"""
        try:
            analytics = await self.get_usage_analytics(user_id, days=30)
            insights = []
            
            if analytics.get("total_tokens", 0) > self.budget.daily_limit * 0.8:
                insights.append({
                    "type": "high_usage_warning",
                    "message": "Token usage is approaching daily limits",
                    "recommendation": "Consider optimizing prompts or increasing budget",
                    "potential_savings": "20-40%"
                })
            
            prompt_breakdown = analytics.get("type_breakdown", {})
            if prompt_breakdown.get("question_generation", {}).get("tokens", 0) > 1000:
                insights.append({
                    "type": "prompt_optimization",
                    "message": "Question generation prompts can be optimized",
                    "recommendation": "Use shorter, more direct prompts",
                    "potential_savings": "15-25%"
                })
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return [] 