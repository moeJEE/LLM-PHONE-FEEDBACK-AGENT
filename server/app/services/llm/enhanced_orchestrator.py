"""
Enhanced LLM Orchestrator with RAG optimization and token management
"""
import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import openai

from .orchestrator import LLMOrchestrator as BaseOrchestrator
from ..rag.enhanced_retriever import EnhancedRAGRetriever, RetrievalContext, RetrievalStrategy
from ..optimization.token_optimizer import TokenOptimizer, PromptType, TokenUsageRecord
from ...core.logging import get_logger
from ...core.config import get_settings

logger = get_logger("services.llm.enhanced_orchestrator")

class EnhancedLLMOrchestrator(BaseOrchestrator):
    """
    Enhanced LLM orchestrator with RAG optimization and token management
    """
    
    def __init__(self):
        super().__init__()
        self.rag_retriever = EnhancedRAGRetriever()
        self.token_optimizer = TokenOptimizer()
        
    async def generate_question_prompt_optimized(
        self,
        question: Dict[str, Any],
        survey: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate optimized question prompt with RAG and token management
        """
        try:
            # Step 1: Check token budget
            estimated_tokens = self._estimate_prompt_tokens(question, conversation_history)
            budget_allowed, budget_reason = await self.token_optimizer.check_token_budget(
                user_id, estimated_tokens, "survey_generation"
            )
            
            if not budget_allowed:
                logger.warning(f"Token budget exceeded for user {user_id}: {budget_reason}")
                # Return simplified prompt if budget exceeded
                return await self._generate_fallback_prompt(question)
            
            # Step 2: Enhanced knowledge retrieval
            retrieval_context = RetrievalContext(
                query=question.get("text", ""),
                conversation_history=conversation_history,
                user_id=user_id,
                survey_context=survey,
                max_tokens=min(estimated_tokens // 2, 1000),  # Use half budget for context
                strategy=RetrievalStrategy.ADAPTIVE
            )
            
            retrieved_knowledge = await self.rag_retriever.retrieve_optimized_context(
                retrieval_context
            )
            
            # Step 3: Optimize prompt for token efficiency
            base_prompt = self.prompt_templates.survey_question_prompt(
                question,
                conversation_history,
                [{"content": r.content, "source": r.source_document} for r in retrieved_knowledge]
            )
            
            optimized_prompt, final_tokens = await self.token_optimizer.optimize_prompt(
                base_prompt,
                PromptType.SURVEY_QUESTION,
                context={
                    "question_type": question.get("question_type"),
                    "survey_title": survey.get("title"),
                    "knowledge_sources": len(retrieved_knowledge)
                }
            )
            
            # Step 4: Generate with CoT reasoning
            cot_result = await self.cot_engine.generate_with_reasoning(optimized_prompt)
            
            # Step 5: Record token usage
            prompt_hash = self.token_optimizer._generate_prompt_hash(
                optimized_prompt, 
                {"user_id": user_id, "question_id": question.get("id")}
            )
            
            await self.token_optimizer.record_token_usage(
                user_id=user_id,
                request_type="survey_generation",
                tokens_used=final_tokens,
                prompt_hash=prompt_hash,
                response_cached=False  # Could implement response caching too
            )
            
            # Step 6: Return enhanced result
            question_text = cot_result.get("output", question["voice_prompt"])
            
            return {
                "text": question_text,
                "original_question": question,
                "cot_reasoning": cot_result.get("reasoning", ""),
                "retrieved_knowledge": [
                    {
                        "content": r.content,
                        "source": r.source_document,
                        "relevance_score": r.relevance_score,
                        "token_count": r.token_count
                    }
                    for r in retrieved_knowledge
                ],
                "optimization_metadata": {
                    "original_tokens": estimated_tokens,
                    "optimized_tokens": final_tokens,
                    "token_savings": estimated_tokens - final_tokens,
                    "knowledge_sources": len(retrieved_knowledge),
                    "retrieval_strategy": retrieval_context.strategy.value
                }
            }
            
        except Exception as e:
            logger.error(f"Error in optimized question generation: {str(e)}", exc_info=True)
            return await self._generate_fallback_prompt(question)
    
    async def analyze_response_optimized(
        self,
        question: Dict[str, Any],
        response: str,
        survey: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Analyze response with enhanced RAG and token optimization
        """
        try:
            # Step 1: Check token budget
            estimated_tokens = self._estimate_analysis_tokens(question, response, conversation_history)
            budget_allowed, budget_reason = await self.token_optimizer.check_token_budget(
                user_id, estimated_tokens, "sentiment_analysis"
            )
            
            if not budget_allowed:
                logger.warning(f"Token budget exceeded for analysis: {budget_reason}")
                return await self._generate_fallback_analysis(question, response)
            
            # Step 2: Contextual knowledge retrieval
            retrieval_context = RetrievalContext(
                query=f"{question.get('text', '')} {response}",
                conversation_history=conversation_history,
                user_id=user_id,
                survey_context=survey,
                max_tokens=min(estimated_tokens // 3, 800),
                strategy=RetrievalStrategy.CONTEXTUAL
            )
            
            retrieved_knowledge = await self.rag_retriever.retrieve_optimized_context(
                retrieval_context
            )
            
            # Step 3: Optimize analysis prompt
            base_prompt = self.prompt_templates.response_analysis_prompt(
                question,
                response,
                conversation_history,
                [{"content": r.content, "source": r.source_document} for r in retrieved_knowledge]
            )
            
            optimized_prompt, final_tokens = await self.token_optimizer.optimize_prompt(
                base_prompt,
                PromptType.SENTIMENT_ANALYSIS,
                context={
                    "response_length": len(response),
                    "question_type": question.get("question_type"),
                    "has_context": len(conversation_history) > 0
                }
            )
            
            # Step 4: Generate analysis with CoT
            cot_result = await self.cot_engine.generate_with_reasoning(optimized_prompt)
            
            # Step 5: Parse and enhance analysis
            analysis = await self._parse_analysis_result(cot_result, question, response)
            
            # Step 6: Record usage
            prompt_hash = self.token_optimizer._generate_prompt_hash(
                optimized_prompt, 
                {"user_id": user_id, "response": response[:100]}
            )
            
            await self.token_optimizer.record_token_usage(
                user_id=user_id,
                request_type="sentiment_analysis",
                tokens_used=final_tokens,
                prompt_hash=prompt_hash
            )
            
            # Add optimization metadata
            analysis["optimization_metadata"] = {
                "original_tokens": estimated_tokens,
                "optimized_tokens": final_tokens,
                "token_savings": estimated_tokens - final_tokens,
                "knowledge_sources": len(retrieved_knowledge)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in optimized response analysis: {str(e)}", exc_info=True)
            return await self._generate_fallback_analysis(question, response)
    
    async def generate_follow_up_optimized(
        self,
        question: Dict[str, Any],
        response: str,
        analysis: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate optimized follow-up questions
        """
        try:
            # Enhanced follow-up generation with context-aware retrieval
            retrieval_context = RetrievalContext(
                query=f"follow up questions for {response} regarding {question.get('text', '')}",
                conversation_history=conversation_history,
                user_id=user_id,
                max_tokens=500,
                strategy=RetrievalStrategy.HYBRID
            )
            
            retrieved_knowledge = await self.rag_retriever.retrieve_optimized_context(
                retrieval_context
            )
            
            # Generate contextual follow-up
            follow_up_prompt = self.prompt_templates.follow_up_prompt(
                question,
                response,
                analysis,
                conversation_history,
                [{"content": r.content} for r in retrieved_knowledge]
            )
            
            optimized_prompt, tokens = await self.token_optimizer.optimize_prompt(
                follow_up_prompt,
                PromptType.RESPONSE_GENERATION
            )
            
            cot_result = await self.cot_engine.generate_with_reasoning(optimized_prompt)
            
            return {
                "text": cot_result.get("output", "Thank you for your response."),
                "cot_reasoning": cot_result.get("reasoning", ""),
                "optimization_metadata": {
                    "tokens_used": tokens,
                    "knowledge_sources": len(retrieved_knowledge)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating optimized follow-up: {str(e)}")
            return {"text": "Thank you for your response.", "error": str(e)}
    
    async def batch_sentiment_analysis(
        self,
        responses: List[Dict[str, Any]],
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Batch process sentiment analysis for better token efficiency
        """
        try:
            # Group responses for batch processing
            batch_size = 10  # Optimal batch size for token efficiency
            results = []
            
            for i in range(0, len(responses), batch_size):
                batch = responses[i:i + batch_size]
                
                # Create batch prompt
                batch_texts = [r["text"] for r in batch]
                batch_prompt = self._create_batch_sentiment_prompt(batch_texts)
                
                # Optimize prompt
                optimized_prompt, tokens = await self.token_optimizer.optimize_prompt(
                    batch_prompt,
                    PromptType.SENTIMENT_ANALYSIS
                )
                
                # Process batch
                cot_result = await self.cot_engine.generate_with_reasoning(optimized_prompt)
                batch_results = self._parse_batch_sentiment_results(cot_result, batch)
                
                results.extend(batch_results)
                
                # Record usage
                await self.token_optimizer.record_token_usage(
                    user_id=user_id,
                    request_type="batch_sentiment_analysis",
                    tokens_used=tokens,
                    prompt_hash=self.token_optimizer._generate_prompt_hash(
                        optimized_prompt, 
                        {"batch_size": len(batch)}
                    )
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch sentiment analysis: {str(e)}")
            return [{"sentiment": "neutral", "confidence": 0.5} for _ in responses]
    
    async def get_optimization_insights(self, user_id: str) -> Dict[str, Any]:
        """
        Get optimization insights and suggestions for the user
        """
        try:
            # Get usage analytics
            analytics = await self.token_optimizer.get_usage_analytics(user_id, days=30)
            
            # Get optimization suggestions
            suggestions = await self.token_optimizer.suggest_optimizations(user_id)
            
            # Calculate potential savings
            total_tokens = analytics.get("total_tokens", 0)
            current_cost = analytics.get("estimated_cost", 0)
            
            # Estimate potential savings with full optimization
            potential_savings = {
                "tokens": int(total_tokens * 0.3),  # 30% average savings
                "cost": current_cost * 0.3,
                "percentage": 30
            }
            
            return {
                "current_usage": analytics,
                "optimization_suggestions": suggestions,
                "potential_savings": potential_savings,
                "optimization_score": self._calculate_optimization_score(analytics),
                "recommendations": self._generate_recommendations(analytics, suggestions)
            }
            
        except Exception as e:
            logger.error(f"Error getting optimization insights: {str(e)}")
            return {}
    
    # Private helper methods
    async def _generate_fallback_prompt(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Generate simple fallback prompt when optimization fails"""
        return {
            "text": question.get("voice_prompt", "Please share your thoughts."),
            "original_question": question,
            "fallback": True,
            "optimization_metadata": {"fallback_reason": "token_budget_exceeded"}
        }
    
    async def _generate_fallback_analysis(
        self, 
        question: Dict[str, Any], 
        response: str
    ) -> Dict[str, Any]:
        """Generate simple fallback analysis"""
        # Simple sentiment analysis without LLM
        sentiment_score = self._simple_sentiment_analysis(response)
        
        return {
            "direct_answer": True,
            "sentiment": sentiment_score["sentiment"],
            "sentiment_score": sentiment_score["score"],
            "key_points": [response[:100]],
            "follow_up_needed": False,
            "fallback": True,
            "condition": self._determine_simple_condition(question, response)
        }
    
    def _simple_sentiment_analysis(self, text: str) -> Dict[str, Any]:
        """Simple rule-based sentiment analysis as fallback"""
        positive_words = ["good", "great", "excellent", "happy", "satisfied", "love", "amazing"]
        negative_words = ["bad", "terrible", "awful", "hate", "disappointed", "poor", "horrible"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return {"sentiment": "positive", "score": 0.7}
        elif negative_count > positive_count:
            return {"sentiment": "negative", "score": -0.7}
        else:
            return {"sentiment": "neutral", "score": 0.0}
    
    def _determine_simple_condition(
        self, 
        question: Dict[str, Any], 
        response: str
    ) -> Optional[str]:
        """Simple condition determination for branching logic"""
        if question.get("question_type") == "numeric":
            try:
                rating = int(response.strip())
                if rating <= 2:
                    return "1-2"
                elif rating == 3:
                    return "3"
                else:
                    return "4-5"
            except ValueError:
                return None
        elif question.get("question_type") == "yes_no":
            response_lower = response.lower().strip()
            if any(word in response_lower for word in ["yes", "y", "1", "true", "correct"]):
                return "yes"
            elif any(word in response_lower for word in ["no", "n", "0", "false", "incorrect"]):
                return "no"
        
        return None
    
    def _estimate_prompt_tokens(
        self, 
        question: Dict[str, Any], 
        conversation_history: List[Dict[str, Any]]
    ) -> int:
        """Estimate tokens needed for prompt generation"""
        base_tokens = 200  # Base prompt template
        question_tokens = len(str(question).split()) * 1.3
        history_tokens = sum(len(str(msg).split()) for msg in conversation_history) * 1.3
        
        return int(base_tokens + question_tokens + history_tokens)
    
    def _estimate_analysis_tokens(
        self, 
        question: Dict[str, Any], 
        response: str, 
        conversation_history: List[Dict[str, Any]]
    ) -> int:
        """Estimate tokens needed for response analysis"""
        base_tokens = 150
        question_tokens = len(str(question).split()) * 1.3
        response_tokens = len(response.split()) * 1.3
        history_tokens = sum(len(str(msg).split()) for msg in conversation_history[-3:]) * 1.3
        
        return int(base_tokens + question_tokens + response_tokens + history_tokens)
    
    async def _parse_analysis_result(
        self, 
        cot_result: Dict[str, Any], 
        question: Dict[str, Any], 
        response: str
    ) -> Dict[str, Any]:
        """Parse and validate analysis result from LLM"""
        try:
            analysis_str = cot_result.get("output", "{}")
            analysis = json.loads(analysis_str)
        except json.JSONDecodeError:
            # Fallback analysis
            analysis = await self._generate_fallback_analysis(question, response)
        
        # Add CoT reasoning
        analysis["cot_reasoning"] = cot_result.get("reasoning", "")
        
        # Ensure required fields
        required_fields = ["direct_answer", "sentiment", "key_points", "follow_up_needed"]
        for field in required_fields:
            if field not in analysis:
                analysis[field] = self._get_default_field_value(field)
        
        # Add condition for branching
        if "condition" not in analysis:
            analysis["condition"] = self._determine_simple_condition(question, response)
        
        return analysis
    
    def _get_default_field_value(self, field: str) -> Any:
        """Get default value for required analysis fields"""
        defaults = {
            "direct_answer": True,
            "sentiment": "neutral",
            "key_points": [],
            "follow_up_needed": False
        }
        return defaults.get(field)
    
    def _create_batch_sentiment_prompt(self, texts: List[str]) -> str:
        """Create optimized batch sentiment analysis prompt"""
        numbered_texts = "\n".join([f"{i+1}. {text}" for i, text in enumerate(texts)])
        
        return f"""
        Analyze sentiment for each text below. Return JSON array with format:
        [{{"id": 1, "sentiment": "positive/negative/neutral", "score": 0.8}}, ...]
        
        Texts:
        {numbered_texts}
        
        JSON Array:
        """
    
    def _parse_batch_sentiment_results(
        self, 
        cot_result: Dict[str, Any], 
        batch: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Parse batch sentiment analysis results"""
        try:
            results_str = cot_result.get("output", "[]")
            results = json.loads(results_str)
            
            # Validate and match with original batch
            parsed_results = []
            for i, item in enumerate(batch):
                if i < len(results):
                    result = results[i]
                    parsed_results.append({
                        **item,
                        "sentiment": result.get("sentiment", "neutral"),
                        "sentiment_score": result.get("score", 0.0),
                        "batch_processed": True
                    })
                else:
                    # Fallback for missing results
                    fallback = self._simple_sentiment_analysis(item.get("text", ""))
                    parsed_results.append({
                        **item,
                        **fallback,
                        "batch_processed": False
                    })
            
            return parsed_results
            
        except Exception as e:
            logger.error(f"Error parsing batch sentiment results: {str(e)}")
            # Return fallback results
            return [
                {
                    **item,
                    **self._simple_sentiment_analysis(item.get("text", "")),
                    "batch_processed": False
                }
                for item in batch
            ]
    
    def _calculate_optimization_score(self, analytics: Dict[str, Any]) -> int:
        """Calculate optimization score (0-100)"""
        score = 100
        
        # Deduct points for low cache hit rate
        cache_rate = analytics.get("cache_hit_rate", 0)
        if cache_rate < 0.3:
            score -= 30
        elif cache_rate < 0.5:
            score -= 15
        
        # Deduct points for high token usage
        daily_avg = analytics.get("total_tokens", 0) / max(1, len(analytics.get("daily_breakdown", {})))
        if daily_avg > self.token_optimizer.budget.daily_limit * 0.8:
            score -= 25
        elif daily_avg > self.token_optimizer.budget.daily_limit * 0.6:
            score -= 10
        
        # Deduct points for inefficient usage patterns
        type_breakdown = analytics.get("type_breakdown", {})
        if type_breakdown.get("sentiment_analysis", {}).get("tokens", 0) > analytics.get("total_tokens", 1) * 0.6:
            score -= 20
        
        return max(0, score)
    
    def _generate_recommendations(
        self, 
        analytics: Dict[str, Any], 
        suggestions: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Based on optimization score
        score = self._calculate_optimization_score(analytics)
        
        if score < 50:
            recommendations.append("Implement response caching to reduce redundant LLM calls")
            recommendations.append("Use batch processing for sentiment analysis")
        
        if score < 70:
            recommendations.append("Optimize prompt templates to reduce token usage")
            recommendations.append("Implement smarter context compression")
        
        # Based on specific usage patterns
        cache_rate = analytics.get("cache_hit_rate", 0)
        if cache_rate < 0.3:
            recommendations.append("Standardize prompt formats to improve cache hit rates")
        
        # Add suggestions from the optimizer
        for suggestion in suggestions[:3]:  # Top 3 suggestions
            recommendations.append(suggestion.get("description", ""))
        
        return recommendations[:5]  # Limit to top 5 recommendations 