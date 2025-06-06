from fastapi import APIRouter, Request, HTTPException, status, Header
from fastapi.responses import JSONResponse, Response
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from bson import ObjectId
import logging
import asyncio

from ..core.config import get_settings
from ..core.logging import get_logger
from ..db.mongodb import MongoDB
from ..services.nexmo_whatsapp_service import NexmoWhatsAppService
from ..services.sentiment.analyzer import SentimentAnalyzer
from ..services.llm.cot_engine import CoTEngine
from ..models.survey import SurveyResult

logger = get_logger("api.nexmo_webhooks")
router = APIRouter(tags=["Nexmo Webhooks"])
settings = get_settings()

# Initialize Nexmo WhatsApp service
nexmo_service = NexmoWhatsAppService()
sentiment_analyzer = SentimentAnalyzer()

@router.post("/inbound", status_code=status.HTTP_200_OK)
async def nexmo_inbound_webhook(
    request: Request,
    x_nexmo_signature: Optional[str] = Header(None)
):
    """
    Handle incoming WhatsApp messages from Nexmo/Vonage
    """
    try:
        # Get request body
        body = await request.body()
        
        if not body:
            logger.warning("⚠️ Empty request body received")
            return JSONResponse({"status": "error", "message": "Empty request body"})
        
        # Parse JSON payload
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON payload: {e}")
            return JSONResponse({"status": "error", "message": "Invalid JSON"}, status_code=400)
        
        logger.info(f"📨 Received Nexmo webhook payload: {json.dumps(payload, indent=2)}")
        
        # Extract message data - handle both direct message and nested structure
        message_data = payload
        if "message" in payload:
            message_data = payload["message"]
        
        from_number = payload.get("from") or message_data.get("from")
        to_number = payload.get("to") or message_data.get("to")
        message_uuid = payload.get("message_uuid") or message_data.get("message_uuid")
        timestamp = payload.get("timestamp") or message_data.get("timestamp")
        
        # Get message type and content - handle various formats
        message_type = payload.get("message_type") or message_data.get("message_type")
        if not message_type and "content" in message_data:
            # Try to detect from content
            content = message_data["content"]
            if "text" in content:
                message_type = "text"
            elif "image" in content:
                message_type = "image"
            elif "file" in content:
                message_type = "file"
        
        # Extract text content
        text_content = None
        if message_type == "text":
            text_content = (payload.get("text") or 
                          message_data.get("text") or
                          (message_data.get("content", {}).get("text") if isinstance(message_data.get("content"), dict) else None))
        
        logger.info(f"📨 Received inbound WhatsApp message: {{\n  \"from\": \"{from_number}\",\n  \"text\": \"{text_content}\",\n  \"timestamp\": \"{timestamp}\",\n  \"message_uuid\": \"{message_uuid}\"\n}}")
        
        # Handle text messages (survey responses or knowledge base queries)
        if message_type == "text" and text_content:
            # First check if this is a survey response (higher priority)
            survey_handled = await handle_survey_response(from_number, text_content)
            
            if survey_handled:
                logger.info(f"✅ Processed as survey response from {from_number}")
            else:
                # Try to handle as knowledge base query only if not a survey response
                knowledge_handled = await handle_knowledge_base_query(from_number, text_content)
                
                if knowledge_handled:
                    logger.info(f"✅ Processed as knowledge base query from {from_number}")
                else:
                    logger.info(f"📝 Regular text message from {from_number}: {text_content}")
                    # Store as a note in survey_results if there's an active survey
                    await store_message_in_survey_context(from_number, text_content, "inbound_message")
        
        # Handle other message types (image, file, etc.) - just log them
        elif message_type in ["image", "file", "audio", "video"]:
            logger.info(f"📎 Received {message_type} message from {from_number}")
            # Store as a note in survey context instead of separate table
            await store_message_in_survey_context(from_number, f"Received {message_type} media", "media_message")
            
        else:
            logger.warning(f"⚠️ Unknown or empty message type: {message_type}")
            # Still try to handle as survey response if there's text
            if text_content:
                survey_handled = await handle_survey_response(from_number, text_content)
                if not survey_handled:
                    await store_message_in_survey_context(from_number, text_content, "unknown_message")
        
        # Return success response
        return JSONResponse({"status": "success", "message": "Message processed"})
        
    except Exception as e:
        logger.error(f"❌ Error processing inbound webhook: {str(e)}", exc_info=True)
        return JSONResponse(
            {"status": "error", "message": "An unexpected error occurred"},
            status_code=500
        )

@router.post("/status", status_code=status.HTTP_200_OK)
async def nexmo_status_webhook(
    request: Request,
    x_nexmo_signature: Optional[str] = Header(None)
):
    """
    Handle message status updates from Nexmo/Vonage
    """
    try:
        # Get request body
        body = await request.body()
        
        if not body:
            logger.warning("⚠️ Empty status webhook body received")
            return JSONResponse({"status": "error", "message": "Empty request body"})
        
        # Parse JSON payload
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in status webhook: {e}")
            return JSONResponse({"status": "error", "message": "Invalid JSON"}, status_code=400)
        
        # Extract status information
        message_uuid = payload.get("message_uuid")
        status_value = payload.get("status")
        timestamp = payload.get("timestamp")
        to_number = payload.get("to")
        from_number = payload.get("from")
        
        logger.info(f"📊 Received message status update: {json.dumps(payload, indent=2)}")
        logger.info(f"📊 Message {message_uuid} status changed to: {status_value}")
        
        # Update status in survey_results instead of whatsapp_messages
        if message_uuid:
            results_collection = MongoDB.get_collection("survey_results")
            
            # Find survey result with this message UUID
            survey_result = await results_collection.find_one({
                "metadata.whatsapp_message_uuid": message_uuid
            })
            
            if survey_result:
                # Update the status in metadata
                await results_collection.update_one(
                    {"_id": survey_result["_id"]},
                    {
                        "$set": {
                            "metadata.last_message_status": status_value,
                            "metadata.last_status_update": datetime.utcnow()
                        },
                        "$push": {
                            "metadata.status_history": {
                                "status": status_value,
                                "timestamp": datetime.fromisoformat(timestamp.replace('Z', '+00:00')) if timestamp else datetime.utcnow()
                            }
                        }
                    }
                )
                logger.info(f"✅ Updated survey result {survey_result['_id']} with status: {status_value}")
            else:
                logger.warning(f"⚠️ Survey result not found for message UUID: {message_uuid}")
        
        return JSONResponse({"status": "success", "message": "Status updated"})
        
    except Exception as e:
        logger.error(f"❌ Error processing status webhook: {str(e)}", exc_info=True)
        return JSONResponse(
            {"status": "error", "message": "An unexpected error occurred"},
            status_code=500
        )

@router.get("/test", status_code=status.HTTP_200_OK)
async def test_nexmo_webhook():
    """Test endpoint to verify Nexmo webhook is working"""
    logger.info("🧪 Nexmo webhook test endpoint called")
    return {
        "status": "success",
        "message": "Nexmo webhook is working",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/send-test-message", status_code=status.HTTP_200_OK)
async def send_test_whatsapp_message(request: Request):
    """
    Test endpoint to send a WhatsApp message via Nexmo
    """
    try:
        body = await request.json()
        to_number = body.get("to_number")
        message_text = body.get("message", "Test message from Nexmo WhatsApp service")
        
        if not to_number:
            return JSONResponse(
                {"status": "error", "message": "to_number is required"}, 
                status_code=400
            )
        
        # Send message
        result = await nexmo_service.send_whatsapp_message(to=to_number, message=message_text)
        
        if result.get('success'):
            logger.info(f"✅ Test message sent successfully: {result.get('message_uuid')}")
        
        return JSONResponse(result)
        
    except Exception as e:
        logger.error(f"❌ Error sending test message: {str(e)}", exc_info=True)
        return JSONResponse(
            {"status": "error", "message": f"Failed to send message: {str(e)}"},
            status_code=500
        )

async def store_message_in_survey_context(phone_number: str, message_content: str, message_type: str):
    """Store message in survey context instead of separate table"""
    try:
        # Normalize phone number
        normalized_number = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        
        # Find any survey results for this phone number (active or completed)
        results_collection = MongoDB.get_collection("survey_results")
        survey_results = await results_collection.find({
            "contact_phone_number": {"$regex": normalized_number}
        }).sort("start_time", -1).limit(1).to_list(length=1)
        
        if survey_results:
            survey_result = survey_results[0]
            # Add message to metadata
            await results_collection.update_one(
                {"_id": survey_result["_id"]},
                {
                    "$push": {
                        "metadata.messages": {
                            "type": message_type,
                            "content": message_content,
                            "timestamp": datetime.utcnow(),
                            "direction": "inbound"
                        }
                    }
                }
            )
            logger.info(f"📝 Stored {message_type} in survey context for {phone_number}")
        else:
            logger.info(f"📝 No survey context found for {phone_number}, message: {message_content}")
    except Exception as e:
        logger.error(f"❌ Error storing message in survey context: {e}")

async def handle_knowledge_base_query(phone_number: str, query_text: str) -> bool:
    """
    Handle incoming WhatsApp knowledge base queries
    Returns True if this was a knowledge base query, False otherwise
    """
    try:
        # Normalize phone number for matching
        normalized_number = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        
        # Find recent knowledge base inquiry calls for this phone number
        calls_collection = MongoDB.get_collection("calls")
        recent_kb_calls = await calls_collection.find({
            "phone_number": {"$regex": normalized_number},
            "metadata.knowledge_base_only": True,
            "metadata.call_type": "knowledge_base_inquiry",
            "created_at": {"$gte": datetime.utcnow() - timedelta(hours=24)}  # Within last 24 hours
        }).sort("created_at", -1).limit(1).to_list(length=1)
        
        if not recent_kb_calls:
            logger.info(f"📊 No recent knowledge base calls found for {phone_number}")
            return False
        
        kb_call = recent_kb_calls[0]
        call_id = str(kb_call["_id"])
        owner_id = kb_call["owner_id"]
        knowledge_base_id = kb_call["metadata"].get("knowledge_base_id", "general")
        
        logger.info(f"📚 Processing knowledge base query for call {call_id}: {query_text}")
        
        # Use RAG system to generate response
        from ..services.rag.enhanced_retriever import EnhancedRAGRetriever, RetrievalContext, RetrievalStrategy
        
        retriever = EnhancedRAGRetriever()
        
        # Create retrieval context with proper filtering
        context = RetrievalContext(
            user_id=owner_id,
            domain="general",
            conversation_history=[],
            document_filters={"owner_id": owner_id, "status": "processed"},
            knowledge_base_id=knowledge_base_id
        )
        
        # Retrieve relevant information
        retrieval_result = await retriever.retrieve_optimized_context(
            query=query_text,
            context=context,
            max_tokens=1000,
            strategy=RetrievalStrategy.SIMPLE
        )
        
        if not retrieval_result.content.strip():
            # No relevant information found
            fallback_message = """🤖 I couldn't find specific information about that topic in our knowledge base.

Could you please:
• Rephrase your question
• Be more specific about what you're looking for
• Ask about our available products/services

What else can I help you with?"""
            
            await nexmo_service.send_whatsapp_message(
                to=phone_number,
                message=fallback_message
            )
            
            # Log the interaction
            await log_knowledge_interaction(call_id, query_text, fallback_message, "fallback")
            return True
        
        # Create response prompt for LLM
        response_prompt = f"""You are a helpful customer service AI assistant. A customer has asked a question, and I've retrieved relevant information from our knowledge base.

Customer Question: {query_text}

Relevant Information from Knowledge Base:
{retrieval_result.content}

Please provide a helpful, accurate, and friendly response to the customer's question based on the retrieved information. If the information doesn't fully answer their question, acknowledge what you can help with and suggest they contact support for more details.

Keep your response:
- Friendly and professional
- Clear and concise  
- Based only on the provided information
- Formatted for WhatsApp messaging

Response:"""
        
        # Generate response using CoT engine
        cot_engine = CoTEngine()
        ai_response = await cot_engine.generate(response_prompt)
        
        if ai_response:
            # Add sources information
            if retrieval_result.sources:
                sources_text = f"\n\n📚 *Sources: {', '.join(retrieval_result.sources[:3])}*"
                ai_response += sources_text
            
            # Send response via WhatsApp
            await nexmo_service.send_whatsapp_message(
                to=phone_number,
                message=ai_response
            )
            
            # Log the successful interaction
            await log_knowledge_interaction(call_id, query_text, ai_response, "success", retrieval_result.tokens_used)
            
            logger.info(f"✅ Sent knowledge base response to {phone_number}")
            return True
        else:
            # LLM generation failed
            error_message = """🤖 I'm having trouble processing your question right now. 

Please try again in a moment, or rephrase your question.

What else can I help you with?"""
            
            await nexmo_service.send_whatsapp_message(
                to=phone_number,
                message=error_message
            )
            
            await log_knowledge_interaction(call_id, query_text, error_message, "error")
            return True
        
    except Exception as e:
        logger.error(f"❌ Error handling knowledge base query: {e}", exc_info=True)
        
        # Send error message to user
        try:
            error_message = """🤖 I'm experiencing technical difficulties. 

Please try your question again, or contact support if the issue persists.

What else can I help you with?"""
            
            await nexmo_service.send_whatsapp_message(
                to=phone_number,
                message=error_message
            )
        except:
            pass  # Don't fail if we can't send error message
        
        return False

async def log_knowledge_interaction(call_id: str, query: str, response: str, status: str, tokens_used: int = 0):
    """Log knowledge base interaction for analytics"""
    try:
        calls_collection = MongoDB.get_collection("calls")
        
        interaction_event = {
            "event_type": "knowledge_base_interaction",
            "description": f"User query: {query[:100]}{'...' if len(query) > 100 else ''}",
            "timestamp": datetime.utcnow(),
            "metadata": {
                "query": query,
                "response": response,
                "status": status,
                "tokens_used": tokens_used,
                "response_length": len(response)
            }
        }
        
        await calls_collection.update_one(
            {"_id": ObjectId(call_id)},
            {
                "$push": {"events": interaction_event},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        logger.info(f"📝 Logged knowledge interaction for call {call_id}")
        
    except Exception as e:
        logger.error(f"❌ Error logging knowledge interaction: {e}")

async def handle_survey_response(phone_number: str, response_text: str) -> bool:
    """
    Handle incoming WhatsApp survey responses
    Returns True if this was a survey response, False otherwise
    """
    try:
        # Normalize phone number for matching
        normalized_number = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        
        # Check if there's a recent knowledge base inquiry (within last 30 minutes)
        # If so, this is likely a knowledge base question, not a survey response
        calls_collection = MongoDB.get_collection("calls")
        recent_kb_calls = await calls_collection.find({
            "phone_number": {"$regex": normalized_number},
            "metadata.knowledge_base_only": True,
            "metadata.call_type": "knowledge_base_inquiry",
            "created_at": {"$gte": datetime.utcnow() - timedelta(minutes=30)}
        }).sort("created_at", -1).limit(1).to_list(length=1)
        
        # If there's a recent knowledge base call, check if response looks like a question
        if recent_kb_calls:
            kb_call = recent_kb_calls[0]
            kb_call_time = kb_call["created_at"]
            
            # Check if response looks like a question rather than a survey answer
            question_indicators = ['what', 'how', 'when', 'where', 'why', 'which', 'who', 'can', 'could', 'would', 'should', 'is', 'are', 'does', 'do', '?']
            response_lower = response_text.lower().strip()
            
            # If it contains question words or is longer than typical survey answers, treat as knowledge query
            looks_like_question = (
                any(indicator in response_lower for indicator in question_indicators) or
                len(response_text.split()) > 5 or  # Questions tend to be longer
                '?' in response_text
            )
            
            if looks_like_question:
                logger.info(f"📚 Response looks like knowledge base question, not survey answer: '{response_text[:50]}'")
                return False
        
        # Find active survey results for this phone number
        results_collection = MongoDB.get_collection("survey_results")
        active_surveys = await results_collection.find({
            "contact_phone_number": {"$regex": normalized_number},
            "completed": False
        }).sort("start_time", -1).to_list(length=None)
        
        if not active_surveys:
            logger.info(f"📊 No active surveys found for {phone_number}")
            return False
        
        # Get the most recent active survey
        active_survey = sorted(active_surveys, key=lambda x: x["start_time"], reverse=True)[0]
        survey_result_id = str(active_survey["_id"])
        
        # Additional check: if the survey is old (more than 2 hours) and there's a recent KB call, 
        # treat as knowledge base query
        survey_age = datetime.utcnow() - active_survey["start_time"]
        if survey_age > timedelta(hours=2) and recent_kb_calls:
            logger.info(f"📚 Survey is old ({survey_age}) and there's recent KB call, treating as knowledge query")
            return False
        
        logger.info(f"📋 Processing survey response for survey result {survey_result_id}")
        
        # Get the survey details
        surveys_collection = MongoDB.get_collection("surveys")
        survey = await surveys_collection.find_one({"_id": ObjectId(active_survey["survey_id"])})
        
        if not survey:
            logger.error(f"❌ Survey {active_survey['survey_id']} not found")
            return False
        
        # Get current question info from metadata
        current_question_index = active_survey.get("metadata", {}).get("current_question_index", 0)
        current_questions = survey["questions"]
        
        if current_question_index >= len(current_questions):
            logger.error(f"❌ Question index {current_question_index} out of range")
            return False
        
        current_question = current_questions[current_question_index]
        question_id = current_question["id"]
        
        # Process the response based on question type
        processed_response = process_survey_answer(current_question, response_text.strip())
        
        if processed_response is None:
            # Invalid response, send help message
            help_message = get_question_help_text(current_question)
            await nexmo_service.send_whatsapp_message(
                to=phone_number,
                message=f"❌ Invalid response. {help_message}"
            )
            return True
        
        # Store the response - fix: use the existing responses and update them
        responses = active_survey.get("responses", {})
        responses[question_id] = processed_response
        
        logger.info(f"💾 Storing response for question {question_id}: {processed_response}")
        
        # Move to next question or complete survey
        next_question_index = current_question_index + 1
        
        if next_question_index >= len(current_questions):
            # Survey completed
            await complete_survey(survey_result_id, responses, phone_number, survey)
        else:
            # Send next question
            await send_next_question(survey_result_id, responses, next_question_index, phone_number, survey)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error handling survey response: {e}", exc_info=True)
        return False

def process_survey_answer(question: dict, response_text: str) -> Any:
    """Process survey answer based on question type"""
    # Handle both 'type' and 'question_type' field names for compatibility
    question_type = question.get("question_type") or question.get("type", "text")
    
    if question_type == "multiple_choice":
        # Try to parse as number first
        try:
            choice_num = int(response_text)
            options = question.get("options", [])
            if 1 <= choice_num <= len(options):
                return {
                    "choice_index": choice_num - 1,
                    "choice_text": options[choice_num - 1],
                    "raw_response": response_text
                }
        except ValueError:
            pass
        
        # Try to match text to options
        options = question.get("options", [])
        for i, option in enumerate(options):
            if response_text.lower() in option.lower() or option.lower() in response_text.lower():
                return {
                    "choice_index": i,
                    "choice_text": option,
                    "raw_response": response_text
                }
        
        return None  # Invalid choice
    
    elif question_type in ["yes_no", "boolean"]:
        response_lower = response_text.lower()
        if response_lower in ["yes", "y", "si", "oui", "1", "true"]:
            return {"value": True, "raw_response": response_text}
        elif response_lower in ["no", "n", "non", "0", "false"]:
            return {"value": False, "raw_response": response_text}
        return None  # Invalid yes/no response
    
    elif question_type in ["numeric", "number", "rating"]:
        try:
            # Try to extract a number from the response
            numbers = re.findall(r'-?\d+\.?\d*', response_text)
            if numbers:
                value = float(numbers[0])
                
                # Check scale boundaries for rating questions
                if question_type == "rating":
                    scale_min = question.get("scale_min", 1)
                    scale_max = question.get("scale_max", 10)
                    if scale_min <= value <= scale_max:
                        return {"value": value, "raw_response": response_text}
                    else:
                        return None  # Outside valid range
                else:
                    # For numeric questions, check min/max if specified
                    min_val = question.get("min_value")
                    max_val = question.get("max_value")
                    if min_val is not None and value < min_val:
                        return None
                    if max_val is not None and value > max_val:
                        return None
                    return {"value": value, "raw_response": response_text}
        except ValueError:
            pass
        return None  # Invalid number
    
    elif question_type == "scale":
        try:
            value = float(response_text.strip())
            scale_min = question.get("scale_min", 1)
            scale_max = question.get("scale_max", 5)
            if scale_min <= value <= scale_max:
                return {"value": value, "raw_response": response_text}
        except ValueError:
            pass
        return None  # Invalid scale value
    
    else:  # text, open_ended, or any other type
        if len(response_text.strip()) > 0:
            # Check character limit if specified
            max_length = question.get("max_length")
            if max_length and len(response_text) > max_length:
                return {"text": response_text[:max_length], "raw_response": response_text, "truncated": True}
            return {"text": response_text.strip(), "raw_response": response_text}
        return None  # Empty response

def get_question_help_text(question: dict) -> str:
    """Generate help text for a question"""
    # Handle both 'type' and 'question_type' field names for compatibility
    question_type = question.get("question_type") or question.get("type", "text")
    
    if question_type == "multiple_choice":
        options = question.get("options", [])
        options_text = "\n".join([f"{i+1}. {option}" for i, option in enumerate(options)])
        return f"Please reply with the NUMBER (1, 2, 3, etc.) or EXACT TEXT of your choice:\n{options_text}"
    elif question_type in ["yes_no", "boolean"]:
        return "Please reply with 'Yes' or 'No'."
    elif question_type == "rating":
        scale_min = question.get("scale_min", 1)
        scale_max = question.get("scale_max", 10)
        return f"Please reply with a NUMBER between {scale_min} and {scale_max}."
    elif question_type == "scale":
        scale_min = question.get("scale_min", 1)
        scale_max = question.get("scale_max", 5)
        scale_labels = question.get("scale_labels", {})
        help_text = f"Please reply with a NUMBER between {scale_min} and {scale_max}"
        if scale_labels:
            if str(scale_min) in scale_labels and str(scale_max) in scale_labels:
                help_text += f" (where {scale_min} = {scale_labels[str(scale_min)]} and {scale_max} = {scale_labels[str(scale_max)]})"
        return help_text + "."
    elif question_type in ["numeric", "number"]:
        min_val = question.get("min_value")
        max_val = question.get("max_value")
        if min_val is not None and max_val is not None:
            return f"Please reply with a NUMBER between {min_val} and {max_val}."
        elif min_val is not None:
            return f"Please reply with a NUMBER (minimum: {min_val})."
        elif max_val is not None:
            return f"Please reply with a NUMBER (maximum: {max_val})."
        else:
            return "Please reply with a NUMBER."
    else:  # text, open_ended
        max_length = question.get("max_length")
        if max_length:
            return f"Please provide your answer (maximum {max_length} characters)."
        else:
            return "Please provide your answer."

async def send_next_question(survey_result_id: str, responses: dict, question_index: int, phone_number: str, survey: dict):
    """Send the next question in the survey"""
    questions = survey["questions"]
    next_question = questions[question_index]
    
    # Format question message
    question_text = f"**Question {question_index + 1}:** {next_question['text']}"
    
    # Handle both 'type' and 'question_type' field names for compatibility
    question_type = next_question.get("question_type") or next_question.get("type", "text")
    
    # Add response instructions based on question type
    if question_type == "multiple_choice" and next_question.get("options"):
        options = next_question["options"]
        options_text = "\n\n" + "\n".join([f"{i+1}. {option}" for i, option in enumerate(options)])
        question_text += options_text
        question_text += "\n\nReply with the NUMBER (1, 2, 3, etc.) or the EXACT TEXT of your choice."
    elif question_type == "rating":
        scale_min = next_question.get("scale_min", 1)
        scale_max = next_question.get("scale_max", 10)
        question_text += f"\n\nPlease rate on a scale of {scale_min} to {scale_max} (where {scale_max} is the highest).\n\nReply with a NUMBER between {scale_min} and {scale_max}."
    elif question_type in ["yes_no", "boolean"]:
        question_text += "\n\nPlease answer with \"Yes\" or \"No\"."
    elif question_type == "scale":
        scale_min = next_question.get("scale_min", 1)
        scale_max = next_question.get("scale_max", 5)
        scale_labels = next_question.get("scale_labels", {})
        question_text += f"\n\nPlease rate on a scale of {scale_min} to {scale_max}"
        if scale_labels:
            if str(scale_min) in scale_labels:
                question_text += f" (where {scale_min} = {scale_labels[str(scale_min)]}"
            if str(scale_max) in scale_labels:
                question_text += f" and {scale_max} = {scale_labels[str(scale_max)]}"
            question_text += ")"
        question_text += f"\n\nReply with a NUMBER between {scale_min} and {scale_max}."
    elif question_type in ["numeric", "number"]:
        min_val = next_question.get("min_value")
        max_val = next_question.get("max_value")
        if min_val is not None and max_val is not None:
            question_text += f"\n\nPlease enter a NUMBER between {min_val} and {max_val}."
        elif min_val is not None:
            question_text += f"\n\nPlease enter a NUMBER (minimum: {min_val})."
        elif max_val is not None:
            question_text += f"\n\nPlease enter a NUMBER (maximum: {max_val})."
        else:
            question_text += "\n\nPlease enter a NUMBER."
    else:  # text or any other type
        char_limit = next_question.get("max_length")
        if char_limit:
            question_text += f"\n\nPlease reply with your answer (maximum {char_limit} characters)."
        else:
            question_text += "\n\nReply with your answer."
    
    # Send the question
    await nexmo_service.send_whatsapp_message(
        to=phone_number,
        message=question_text
    )
    
    # Update survey result
    results_collection = MongoDB.get_collection("survey_results")
    await results_collection.update_one(
        {"_id": ObjectId(survey_result_id)},
        {
            "$set": {
                "responses": responses,
                "metadata.current_question_id": next_question["id"],
                "metadata.current_question_index": question_index
            }
        }
    )
    
    logger.info(f"📨 Sent question {question_index + 1} for survey result {survey_result_id}")

async def complete_survey(survey_result_id: str, responses: dict, phone_number: str, survey: dict):
    """Complete the survey and send thank you message"""
    
    # Calculate completion time
    end_time = datetime.utcnow()
    
    # Get survey result to calculate duration
    results_collection = MongoDB.get_collection("survey_results")
    survey_result = await results_collection.find_one({"_id": ObjectId(survey_result_id)})
    
    if survey_result:
        start_time = survey_result["start_time"]
        duration_seconds = int((end_time - start_time).total_seconds())
    else:
        duration_seconds = 0
    
    # 🚀 FIRST: Send thank you message immediately (don't make user wait!)
    outro_message = survey.get("outro_message", "Thank you for completing our survey! Your feedback is valuable to us.")
    await nexmo_service.send_whatsapp_message(
        to=phone_number,
        message=f"🎉 {outro_message}"
    )
    logger.info(f"✅ Thank you message sent immediately to {phone_number}")
    
    # Update survey result as completed (without sentiment analysis first)
    await results_collection.update_one(
        {"_id": ObjectId(survey_result_id)},
        {
            "$set": {
                "responses": responses,
                "completed": True,
                "end_time": end_time,
                "duration_seconds": duration_seconds,
                "sentiment_analysis_pending": True  # Flag for background processing
            }
        }
    )
    logger.info(f"✅ Survey marked as completed for survey result {survey_result_id}")
    
    # Update call status if there's a call_id (without sentiment first)
    if survey_result and survey_result.get("call_id"):
        calls_collection = MongoDB.get_collection("calls")
        await calls_collection.update_one(
            {"_id": ObjectId(survey_result["call_id"])},
            {
                "$set": {
                    "status": "completed",
                    "updated_at": end_time,
                    "metadata.survey_completed": True,
                    "metadata.survey_completion_time": end_time.isoformat()
                }
            }
        )
    
    # 🎯 SECOND: Perform sentiment analysis in background (user doesn't wait)
    asyncio.create_task(analyze_sentiment_background(survey_result_id, responses, survey))
    
    logger.info(f"✅ Survey completed for survey result {survey_result_id}")
    logger.info(f"📊 Final responses: {responses}")
    logger.info(f"🔄 Sentiment analysis started in background")

async def analyze_sentiment_background(survey_result_id: str, responses: dict, survey: dict):
    """Perform sentiment analysis in background after user has received thank you message"""
    try:
        logger.info(f"🎯 Starting background sentiment analysis for {survey_result_id}")
        
        # Process responses in parallel for speed
        sentiment_tasks = []
        question_map = {}
        
        for question_id, response_data in responses.items():
            # Find the question for context
            question = next((q for q in survey["questions"] if q["id"] == question_id), None)
            if not question:
                continue
                
            # Extract text for sentiment analysis
            response_text = ""
            if isinstance(response_data, dict):
                if "text" in response_data:
                    response_text = response_data["text"]
                elif "raw_response" in response_data:
                    response_text = response_data["raw_response"]
            elif isinstance(response_data, str):
                response_text = response_data
            
            if response_text and len(response_text.strip()) > 2:
                # Create async task for this response
                task = asyncio.create_task(
                    analyze_single_response(response_text, question, survey, question_id)
                )
                sentiment_tasks.append(task)
                question_map[question_id] = response_text
        
        # Wait for all sentiment analyses to complete (with timeout)
        try:
            sentiment_results = await asyncio.wait_for(
                asyncio.gather(*sentiment_tasks, return_exceptions=True),
                timeout=30.0  # 30 second timeout for all analyses
            )
        except asyncio.TimeoutError:
            logger.warning(f"⏰ Sentiment analysis timeout for {survey_result_id}")
            sentiment_results = [None] * len(sentiment_tasks)
        
        # Process results
        sentiment_scores = {}
        for i, result in enumerate(sentiment_results):
            if isinstance(result, Exception):
                logger.error(f"❌ Sentiment analysis failed for task {i}: {result}")
                continue
            
            if result and result.get("question_id"):
                question_id = result["question_id"]
                if result.get("success", False):
                    sentiment_scores[question_id] = result.get("score", 0.0)
                    logger.info(f"📊 Sentiment for {question_id}: {result.get('score', 0.0)}")
                else:
                    sentiment_scores[question_id] = 0.0
                    logger.warning(f"⚠️ Sentiment analysis failed for {question_id}")
        
        # Calculate overall sentiment
        overall_sentiment = 0.0
        if sentiment_scores:
            overall_sentiment = sum(sentiment_scores.values()) / len(sentiment_scores)
        
        logger.info(f"📊 Overall sentiment score: {overall_sentiment}")
        
        # Update survey result with sentiment analysis results
        results_collection = MongoDB.get_collection("survey_results")
        await results_collection.update_one(
            {"_id": ObjectId(survey_result_id)},
            {
                "$set": {
                    "sentiment_scores": sentiment_scores,
                    "overall_sentiment": overall_sentiment,
                    "sentiment_analysis_pending": False,
                    "sentiment_analysis_completed_at": datetime.utcnow()
                }
            }
        )
        
        # Update call status with sentiment
        survey_result = await results_collection.find_one({"_id": ObjectId(survey_result_id)})
        if survey_result and survey_result.get("call_id"):
            calls_collection = MongoDB.get_collection("calls")
            await calls_collection.update_one(
                {"_id": ObjectId(survey_result["call_id"])},
                {
                    "$set": {
                        "metadata.overall_sentiment": overall_sentiment,
                        "metadata.sentiment_analysis_completed": True
                    }
                }
            )
        
        logger.info(f"✅ Background sentiment analysis completed for {survey_result_id}")
        logger.info(f"📊 Sentiment scores: {sentiment_scores}")
        logger.info(f"📊 Overall sentiment: {overall_sentiment}")
        
    except Exception as e:
        logger.error(f"❌ Error in background sentiment analysis for {survey_result_id}: {e}")
        
        # Mark sentiment analysis as failed but don't crash
        try:
            results_collection = MongoDB.get_collection("survey_results")
            await results_collection.update_one(
                {"_id": ObjectId(survey_result_id)},
                {
                    "$set": {
                        "sentiment_analysis_pending": False,
                        "sentiment_analysis_failed": True,
                        "sentiment_analysis_error": str(e),
                        "overall_sentiment": 0.0  # Default neutral sentiment
                    }
                }
            )
        except Exception as update_error:
            logger.error(f"❌ Failed to update sentiment analysis error: {update_error}")

async def analyze_single_response(response_text: str, question: dict, survey: dict, question_id: str) -> dict:
    """Analyze sentiment for a single response with error handling"""
    try:
        # Use the optimized sentiment analyzer
        sentiment_result = await sentiment_analyzer.analyze_survey_response(
            response=response_text,
            question=question,
            survey_context=survey
        )
        
        sentiment_result["question_id"] = question_id
        return sentiment_result
        
    except Exception as e:
        logger.error(f"❌ Error analyzing sentiment for question {question_id}: {e}")
        return {
            "question_id": question_id,
            "success": False,
            "error": str(e),
            "score": 0.0
        } 