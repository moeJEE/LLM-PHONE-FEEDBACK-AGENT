from typing import Dict, Any, List, Optional
import json
import asyncio
from datetime import datetime

from ...core.config import get_settings
from ...core.logging import get_logger
from ...db.vectordb import VectorDB
from .prompt_templates import PromptTemplates
from .cot_engine import CoTEngine
from .action_tools import ActionTools
from openai import AsyncOpenAI
from ...services.optimization.token_optimizer import TokenOptimizer, TokenUsageRecord, PromptType

logger = get_logger("services.llm.orchestrator")
settings = get_settings()

class LLMOrchestrator:
    """
    Main orchestrator for LLM interactions, manages the flow of Chain-of-Thought (CoT) reasoning
    and coordinates knowledge retrieval, prompt generation, and response processing.
    """
    
    def __init__(self):
        self.cot_engine = CoTEngine()
        self.prompt_templates = PromptTemplates()
        self.action_tools = ActionTools()
        self.vector_db = VectorDB()
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.token_optimizer = TokenOptimizer()
    
    async def initialize_survey_conversation(self, survey: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize a new survey conversation by setting up the system prompt
        and generating the welcome message.
        
        Args:
            survey: Survey configuration
            
        Returns:
            Dict: Initial conversation state
        """
        # Prepare survey information for system prompt
        survey_info = {
            "company_name": survey.get("metadata", {}).get("company_name", "Our Company"),
            "title": survey.get("title", "Customer Feedback Survey"),
            "purpose": survey.get("description", "gather valuable feedback"),
            "survey_flow": self._format_survey_flow(survey["questions"]),
            "knowledge_base_info": "No specific knowledge base available."
        }
        
        # Generate system prompt
        system_prompt = self.prompt_templates.survey_system_prompt(survey_info)
        
        # Initialize conversation with system prompt
        initial_state = {
            "system_prompt": system_prompt,
            "conversation_history": [],
            "survey_id": str(survey["_id"]),
            "current_question_index": 0,
            "started_at": datetime.utcnow().isoformat()
        }
        
        # Generate welcome message
        welcome_message = survey.get("intro_message", "Welcome to our survey. Thank you for participating.")
        
        return {
            **initial_state,
            "welcome_message": welcome_message
        }
    
    async def generate_question_prompt(
        self,
        question: Dict[str, Any],
        survey: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate the prompt for the next question using Chain-of-Thought (CoT) reasoning.
        
        Args:
            question: The question to ask
            survey: The survey configuration
            conversation_history: History of the conversation so far
            user_id: The user ID
            
        Returns:
            Dict: Generated prompt and metadata
        """
        try:
            # Retrieve relevant knowledge if any
            retrieved_knowledge = await self._retrieve_relevant_knowledge(
                survey, 
                question, 
                conversation_history
            )
            
            # Generate the prompt using CoT
            prompt = self.prompt_templates.survey_question_prompt(
                question,
                conversation_history,
                retrieved_knowledge
            )
            
            # Send to LLM with CoT reasoning
            cot_result = await self.cot_engine.generate_with_reasoning(prompt)
            
            # Extract the final question text from CoT reasoning
            question_text = cot_result.get("output", question["voice_prompt"])
            
            # Track usage
            await self._track_usage(
                PromptType.QUESTION_GENERATION,
                prompt,
                question_text,
                user_id
            )
            
            return {
                "text": question_text,
                "original_question": question,
                "cot_reasoning": cot_result.get("reasoning", ""),
                "retrieved_knowledge": retrieved_knowledge
            }
            
        except Exception as e:
            logger.error(f"Error generating question prompt: {str(e)}", exc_info=True)
            # Fallback to the original voice prompt
            return {
                "text": question["voice_prompt"],
                "original_question": question,
                "error": str(e)
            }
    
    async def analyze_response(
        self,
        question: Dict[str, Any],
        response: str,
        survey: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Analyze a customer's response to a question using Chain-of-Thought (CoT) reasoning.
        
        Args:
            question: The question that was asked
            response: The customer's response
            survey: The survey configuration
            conversation_history: History of the conversation so far
            user_id: The user ID
            
        Returns:
            Dict: Analysis results including sentiment, classification, and next steps
        """
        try:
            # Retrieve relevant knowledge if any
            retrieved_knowledge = await self._retrieve_relevant_knowledge(
                survey, 
                question, 
                conversation_history,
                query=response
            )
            
            # Generate the prompt for response analysis
            prompt = self.prompt_templates.response_analysis_prompt(
                question,
                response,
                conversation_history,
                retrieved_knowledge
            )
            
            # Send to LLM with CoT reasoning
            cot_result = await self.cot_engine.generate_with_reasoning(prompt)
            
            # Extract structured analysis from the CoT result
            analysis_str = cot_result.get("output", "{}")
            try:
                # Try to parse JSON from the output
                analysis = json.loads(analysis_str)
            except json.JSONDecodeError:
                # If output is not valid JSON, create a simple result
                analysis = {
                    "direct_answer": True,
                    "sentiment": "neutral",
                    "key_points": [],
                    "follow_up_needed": False
                }
            
            # Add CoT reasoning to the result
            analysis["cot_reasoning"] = cot_result.get("reasoning", "")
            analysis["retrieved_knowledge"] = retrieved_knowledge
            
            # Determine branching condition for question logic
            if question["question_type"] == "numeric":
                try:
                    rating = int(response.strip())
                    if rating <= 2:
                        analysis["condition"] = "1-2"
                    elif rating == 3:
                        analysis["condition"] = "3"
                    else:  # 4-5
                        analysis["condition"] = "4-5"
                except ValueError:
                    analysis["condition"] = None
            elif question["question_type"] == "yes_no":
                response_lower = response.lower().strip()
                if response_lower in ["yes", "1", "y"]:
                    analysis["condition"] = "yes"
                elif response_lower in ["no", "2", "n"]:
                    analysis["condition"] = "no"
                else:
                    analysis["condition"] = None
            elif question["question_type"] == "multiple_choice":
                # For multiple choice, try to match the response with one of the options
                options = question.get("options", [])
                best_match = None
                
                if options:
                    # Try exact match first
                    for option in options:
                        if response.lower().strip() == option.lower():
                            best_match = option
                            break
                    
                    # If no exact match, use the LLM to find the closest match
                    if not best_match and analysis.get("selected_option"):
                        best_match = analysis["selected_option"]
                
                analysis["condition"] = best_match
            
            # Track usage
            await self._track_usage(
                PromptType.RESPONSE_ANALYSIS,
                prompt,
                json.dumps(analysis),
                user_id
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing response: {str(e)}", exc_info=True)
            # Return a minimal result in case of error
            return {
                "direct_answer": True,
                "sentiment": "neutral",
                "error": str(e)
            }
    
    async def generate_follow_up(
        self,
        question: Dict[str, Any],
        response: str,
        analysis: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate a follow-up response based on the customer's answer and analysis.
        
        Args:
            question: The question that was asked
            response: The customer's response
            analysis: The analysis of the response
            conversation_history: History of the conversation so far
            user_id: The user ID
            
        Returns:
            Dict: Generated follow-up response
        """
        # Check if follow-up is needed based on analysis
        if not analysis.get("follow_up_needed", False):
            return {"text": None}
        
        # Generate a prompt for the follow-up
        prompt = f"""
Based on the customer's response: "{response}"
And our analysis showing: {json.dumps(analysis)}

Generate a brief, natural follow-up response or clarification question.
This should acknowledge what they said and ask for more information in a conversational way.
"""
        
        # Send to LLM
        result = await self.cot_engine.generate(prompt)
        
        # Track usage
        await self._track_usage(
            PromptType.FOLLOW_UP_GENERATION,
            prompt,
            result,
            user_id
        )
        
        return {
            "text": result,
            "original_question": question,
            "analysis": analysis
        }
    
    async def _retrieve_relevant_knowledge(
        self,
        survey: Dict[str, Any],
        question: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge from the vector database for the current context.
        
        Args:
            survey: The survey configuration
            question: The current question
            conversation_history: Conversation history
            query: Optional specific query to search for
            
        Returns:
            List: Retrieved knowledge items
        """
        # If there's no knowledge collection specified, return empty
        knowledge_base_id = survey.get("metadata", {}).get("knowledge_base_id")
        if not knowledge_base_id:
            return []
        
        try:
            # Construct search query
            if not query:
                # Use the question as the query
                query = question.get("text", "")
                
                # Add recent conversation context
                if conversation_history:
                    last_exchanges = conversation_history[-2:] if len(conversation_history) >= 2 else conversation_history
                    context = " ".join([exchange.get("text", "") for exchange in last_exchanges])
                    query = f"{query} {context}"
            
            # Generate embedding for query
            from ..document_processor.embedding_generator import EmbeddingGenerator
            embedding_generator = EmbeddingGenerator()
            query_embedding = embedding_generator.generate_embeddings([query])[0]
            
            # Search vector DB
            results = self.vector_db.similarity_search(
                collection_name=f"kb_{knowledge_base_id}",
                query_embedding=query_embedding,
                top_k=3
            )
            
            return results
        except Exception as e:
            logger.error(f"Error retrieving knowledge: {str(e)}", exc_info=True)
            return []
    
    def _format_survey_flow(self, questions: List[Dict[str, Any]]) -> str:
        """Format the survey questions for the system prompt"""
        if not questions:
            return "No questions defined."
        
        flow_text = "Survey consists of the following questions:\n"
        
        for i, q in enumerate(questions):
            flow_text += f"{i+1}. {q['text']} (Type: {q['question_type']})"
            
            if q.get("follow_up_logic"):
                flow_text += " - Has conditional logic."
            
            flow_text += "\n"
        
        return flow_text

    async def _track_usage(self, 
                          prompt_type: PromptType, 
                          input_text: str, 
                          output_text: str, 
                          user_id: str,
                          model: str = "gpt-4o-mini"):
        """Track token usage and cost for analytics"""
        try:
            # Estimate tokens (rough approximation)
            input_tokens = len(input_text.split()) * 1.3  # ~1.3 tokens per word
            output_tokens = len(output_text.split()) * 1.3
            total_tokens = int(input_tokens + output_tokens)
            
            # Calculate cost based on model
            cost_per_1k = {
                "gpt-4o-mini": 0.00015,  # Input: $0.15/1M tokens
                "gpt-4": 0.03,
                "gpt-3.5-turbo": 0.002
            }.get(model, 0.002)
            
            cost = (total_tokens / 1000) * cost_per_1k
            
            # Create usage record
            usage_record = TokenUsageRecord(
                timestamp=datetime.utcnow(),
                prompt_type=prompt_type,
                input_tokens=int(input_tokens),
                output_tokens=int(output_tokens),
                total_tokens=total_tokens,
                cost=cost,
                user_id=user_id,
                optimization_applied=False
            )
            
            # Record in database
            await self.token_optimizer.record_usage(usage_record)
            
            logger.info(f"Usage tracked: {total_tokens} tokens, ${cost:.4f} for {prompt_type.value}")
            
        except Exception as e:
            logger.error(f"Error tracking usage: {e}")