"""
Test endpoints for WhatsApp integration - No authentication required
"""

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from app.services.nexmo_whatsapp_service import NexmoWhatsAppService
from app.db.mongodb import MongoDB
from bson import ObjectId

router = APIRouter(prefix="/test-whatsapp", tags=["WhatsApp Testing"])
logger = logging.getLogger(__name__)

class WhatsAppTestRequest(BaseModel):
    phone_number: str
    survey_id: str
    message: Optional[str] = None

class WhatsAppTestResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

@router.post("/send-survey", response_model=WhatsAppTestResponse)
async def test_send_whatsapp_survey(request: WhatsAppTestRequest):
    """
    Test endpoint to send WhatsApp survey - NO AUTHENTICATION REQUIRED
    This is for testing purposes only
    """
    try:
        # Initialize WhatsApp service
        whatsapp_service = NexmoWhatsAppService()
        
        # Check if survey exists
        surveys_collection = MongoDB.get_collection("surveys")
        if not ObjectId.is_valid(request.survey_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid survey ID format"
            )
        
        survey = await surveys_collection.find_one({"_id": ObjectId(request.survey_id)})
        if not survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey not found: {request.survey_id}"
            )
        
        # Get first question
        questions = survey.get("questions", [])
        if not questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Survey has no questions"
            )
        
        first_question = questions[0]
        
        # Create message text
        intro_message = survey.get("intro_message", "Hello! We would like your feedback.")
        question_text = first_question.get("text", "Please provide your feedback.")
        
        message_text = f"{intro_message}\n\n{question_text}"
        
        if first_question.get("question_type") == "numeric":
            message_text += "\n\nPlease respond with a number (1-5)."
        elif first_question.get("question_type") == "yes_no":
            message_text += "\n\nPlease respond with 'yes' or 'no'."
        else:
            message_text += "\n\nPlease respond with your answer."
        
        # Send WhatsApp message
        result = await whatsapp_service.send_whatsapp_message(
            to=request.phone_number,
            message=message_text
        )
        
        if result.get("success"):
            # Create survey result record
            from app.models.survey import SurveyResult
            
            survey_result = SurveyResult(
                survey_id=request.survey_id,
                call_id=None,  # No call for this test
                contact_phone_number=request.phone_number,
                start_time=datetime.utcnow(),
                completed=False,
                responses=[],
                metadata={
                    "test_mode": True,
                    "whatsapp_message_uuid": result.get("message_uuid"),
                    "current_question_index": 0,
                    "total_questions": len(questions)
                }
            )
            
            # Store in database
            survey_results_collection = MongoDB.get_collection("survey_results")
            survey_result_doc = await survey_results_collection.insert_one(
                survey_result.dict(by_alias=True)
            )
            
            logger.info(f"✅ Test WhatsApp survey sent to {request.phone_number}")
            logger.info(f"   Survey ID: {request.survey_id}")
            logger.info(f"   Message UUID: {result.get('message_uuid')}")
            logger.info(f"   Survey Result ID: {survey_result_doc.inserted_id}")
            
            return WhatsAppTestResponse(
                success=True,
                message=f"WhatsApp survey sent successfully to {request.phone_number}",
                data={
                    "phone_number": request.phone_number,
                    "survey_id": request.survey_id,
                    "survey_title": survey.get("title", "Unknown"),
                    "message_uuid": result.get("message_uuid"),
                    "survey_result_id": str(survey_result_doc.inserted_id),
                    "first_question": question_text,
                    "question_type": first_question.get("question_type"),
                    "total_questions": len(questions)
                }
            )
        else:
            logger.error(f"❌ Failed to send WhatsApp survey: {result.get('error')}")
            return WhatsAppTestResponse(
                success=False,
                message=f"Failed to send WhatsApp survey: {result.get('error', 'Unknown error')}",
                data={"error_details": result}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in test WhatsApp survey: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/send-message", response_model=WhatsAppTestResponse)
async def test_send_whatsapp_message(
    phone_number: str = Query(..., description="Phone number to send to"),
    message: str = Query(..., description="Message to send")
):
    """
    Test endpoint to send a simple WhatsApp message - NO AUTHENTICATION REQUIRED
    """
    try:
        whatsapp_service = NexmoWhatsAppService()
        
        result = await whatsapp_service.send_whatsapp_message(
            to=phone_number,
            message=message
        )
        
        if result.get("success"):
            logger.info(f"✅ Test WhatsApp message sent to {phone_number}")
            return WhatsAppTestResponse(
                success=True,
                message=f"WhatsApp message sent successfully to {phone_number}",
                data={
                    "phone_number": phone_number,
                    "message": message,
                    "message_uuid": result.get("message_uuid"),
                    "timestamp": result.get("timestamp")
                }
            )
        else:
            logger.error(f"❌ Failed to send WhatsApp message: {result.get('error')}")
            return WhatsAppTestResponse(
                success=False,
                message=f"Failed to send WhatsApp message: {result.get('error', 'Unknown error')}",
                data={"error_details": result}
            )
            
    except Exception as e:
        logger.error(f"❌ Error in test WhatsApp message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/status", response_model=WhatsAppTestResponse)
async def test_whatsapp_status():
    """
    Check WhatsApp service status - NO AUTHENTICATION REQUIRED
    """
    try:
        whatsapp_service = NexmoWhatsAppService()
        
        # Check if in simulation mode
        simulation_mode = whatsapp_service.simulation_mode
        
        return WhatsAppTestResponse(
            success=True,
            message="WhatsApp service status check",
            data={
                "simulation_mode": simulation_mode,
                "service_initialized": True,
                "nexmo_from_number": whatsapp_service.settings.NEXMO_WHATSAPP_FROM
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error checking WhatsApp status: {e}")
        return WhatsAppTestResponse(
            success=False,
            message=f"WhatsApp service error: {str(e)}"
        ) 