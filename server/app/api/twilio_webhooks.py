from bson import ObjectId
from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse, Response
import hmac
import hashlib
import base64
from urllib.parse import parse_qs
from datetime import datetime
from typing import Dict, Any, Optional, List

from ..core.config import get_settings
from ..core.logging import get_logger
from ..db.mongodb import MongoDB
from ..models.call import CallEvent, CallStatus
from ..services.llm.orchestrator import LLMOrchestrator
from ..services.telephony.twilio_connector import TwilioConnector
from ..services.telephony.speech_to_text import STTService
from ..services.telephony.text_to_speech import TTSService

logger = get_logger("api.twilio_webhooks")
router = APIRouter()
settings = get_settings()

# Initialize services
twilio_connector = TwilioConnector()
stt_service = STTService()
tts_service = TTSService()

# Helper to validate Twilio signatures
async def validate_twilio_signature_disabled(request: Request) -> Dict[str, Any]:
    """
    TEMPORARY: Skip all signature validation for testing real calls
    """
    logger.info("SIGNATURE VALIDATION DISABLED - Processing webhook")
    body_bytes = await request.body()
    body = body_bytes.decode()
    form_data = parse_qs(body)
    form_dict = {k: v[0] for k, v in form_data.items()}
    return form_dict


@router.post("/voice", response_class=Response)
async def twilio_voice_webhook(form_data: Dict[str, Any] = Depends(validate_twilio_signature_disabled)):
    """
    Webhook for incoming Twilio voice calls.
    This is called when a call is initiated.
    """
    try:
        call_sid = form_data.get("CallSid")
        from_number = form_data.get("From")
        to_number = form_data.get("To")
        logger.info(f"Received voice webhook for call {call_sid} from {from_number} to {to_number}")

        # Create or find the call in the database
        calls_collection = MongoDB.get_collection("calls")
        
        # Check if call already exists
        existing_call = await calls_collection.find_one({"twilio_call_sid": call_sid})
        
        if not existing_call:
            # Create a new call document
            # We'll use a default survey for incoming calls - you can modify this logic
            surveys_collection = MongoDB.get_collection("surveys")
            
            # Find the first active survey (you might want to implement routing logic here)
            default_survey = await surveys_collection.find_one({"status": "active"})
            if not default_survey:
                # If no active survey, create a basic one or use a default ID
                # For now, let's use the survey ID we've been testing with
                default_survey_id = "6839f8e8930283a337d2f929"
            else:
                default_survey_id = str(default_survey["_id"])
            
            from ..models.call import CallCreate, CallStatus
            
            # Create call document
            call_doc = {
                "phone_number": from_number,
                "survey_id": default_survey_id,
                "twilio_call_sid": call_sid,
                "status": CallStatus.IN_PROGRESS.value,
                "scheduled_at": datetime.utcnow(),
                "started_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "metadata": {
                    "current_question_index": 0,
                    "survey_started": False,
                    "conversation_history": [],
                    "twilio_from": from_number,
                    "twilio_to": to_number,
                    "call_direction": "inbound"
                },
                "events": [
                    {
                        "event_type": "call_received",
                        "description": f"Inbound call received from {from_number}",
                        "timestamp": datetime.utcnow()
                    }
                ]
            }
            
            # Insert the call
            result = await calls_collection.insert_one(call_doc)
            logger.info(f"Created call document with ID: {result.inserted_id}")
        else:
            logger.info(f"Call {call_sid} already exists in database")

        # Instanciation du connecteur Twilio
        twilio_connector = TwilioConnector()

        # Generate welcome TwiML
        twiml = twilio_connector.generate_welcome_twiml()

        return Response(content=twiml, media_type="application/xml")
    
    except Exception as e:
        logger.error(f"Error in voice webhook: {str(e)}", exc_info=True)
        # En cas d'erreur, utiliser également le connecteur pour générer un TwiML d'erreur.
        twilio_connector = TwilioConnector()
        twiml = twilio_connector.generate_error_twiml("An unexpected error occurred.")
        return Response(content=twiml, media_type="application/xml")


@router.post("/gather", response_class=Response)
async def twilio_gather_webhook(form_data: Dict[str, Any] = Depends(validate_twilio_signature_disabled)):
    """
    Webhook for Twilio <Gather> actions.
    This is called when the user provides input during a call.
    """
    try:
        call_sid = form_data.get("CallSid")
        digits = form_data.get("Digits", "")
        speech_result = form_data.get("SpeechResult", "")
        
        # Log input received (without sensitive data)
        input_type = "digits" if digits else "speech" if speech_result else "none"
        logger.info(f"Gather input received - Type: {input_type}")
        
        # Get call from database
        calls_collection = MongoDB.get_collection("calls")
        call = await calls_collection.find_one({"twilio_call_sid": call_sid})
        if not call:
            logger.warning(f"Call not found for SID: {call_sid}")
            twilio_connector = TwilioConnector()
            twiml = twilio_connector.generate_error_twiml("Call not found.")
            return Response(content=twiml, media_type="application/xml")
        
        # Check if this is the initial "press any key to start" input
        current_index = call.get("metadata", {}).get("current_question_index", 0)
        survey_started = call.get("metadata", {}).get("survey_started", False)
        
        # If survey hasn't started yet, this is just the initialization input
        if not survey_started:
            logger.info(f"Initializing survey for call {call_sid}")
            
            # Retrieve the survey associated with the call
            surveys_collection = MongoDB.get_collection("surveys")
            survey_id_str = call.get("survey_id")
            logger.debug(f"Survey ID from call: {survey_id_str}")
            try:
                survey_obj_id = ObjectId(survey_id_str)
            except Exception as e:
                logger.error("Error converting survey_id to ObjectId", exc_info=True)
                twilio_connector = TwilioConnector()
                twiml = twilio_connector.generate_error_twiml("Survey not found.")
                return Response(content=twiml, media_type="application/xml")

            if not survey_obj_id:
                logger.warning(f"Cannot convert survey_id: {survey_id_str}")
                twilio_connector = TwilioConnector()
                twiml = twilio_connector.generate_error_twiml("Survey not found.")
                return Response(content=twiml, media_type="application/xml")
            
            survey = await surveys_collection.find_one({"_id": survey_obj_id})
            if not survey:
                logger.warning(f"Survey not found for call {call_sid}")
                twilio_connector = TwilioConnector()
                twiml = twilio_connector.generate_error_twiml("Survey not found.")
                return Response(content=twiml, media_type="application/xml")
            
            # Mark survey as started and prepare first question
            await calls_collection.update_one(
                {"twilio_call_sid": call_sid},
                {
                    "$set": {
                        "metadata.survey_started": True,
                        "metadata.current_question_index": 0,
                        "metadata.conversation_history": [],
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Get the first question
            if not survey.get("questions") or len(survey["questions"]) == 0:
                twilio_connector = TwilioConnector()
                twiml = twilio_connector.generate_error_twiml("No questions found in survey.")
                return Response(content=twiml, media_type="application/xml")
            
            first_question = survey["questions"][0]
            logger.info(f"Starting survey with first question: {first_question.get('text', 'N/A')}")
            
            # Generate TwiML for the first question
            twilio_connector = TwilioConnector()
            twiml = twilio_connector.generate_question_twiml(
                first_question.get("voice_prompt", first_question.get("text", "Please provide your response.")),
                question_type=first_question["question_type"],
                options=first_question.get("options", [])
            )
            logger.info(f"Generated TwiML for first question")
            return Response(content=twiml, media_type="application/xml")
        
        # If we reach here, the survey has already started, so process the actual response
        twilio_connector = TwilioConnector()
        
        # Retrieve the survey associated with the call,
        # converting the survey_id (stored as a string) into an ObjectId.
        surveys_collection = MongoDB.get_collection("surveys")
        survey_id_str = call.get("survey_id")
        logger.debug(f"Survey ID from call: {survey_id_str}")
        try:
            survey_obj_id = ObjectId(survey_id_str)
        except Exception as e:
            logger.error("Erreur lors de la conversion du survey_id en ObjectId", exc_info=True)
            survey_obj_id = None

        if not survey_obj_id:
            logger.warning(f"Cannot convert survey_id: {survey_id_str}")
            twiml = twilio_connector.generate_error_twiml("Survey not found.")
            return Response(content=twiml, media_type="application/xml")
        
        survey = await surveys_collection.find_one({"_id": survey_obj_id})
        if not survey:
            logger.warning(f"Survey not found for call {call_sid}")
            twiml = twilio_connector.generate_error_twiml("Survey not found.")
            return Response(content=twiml, media_type="application/xml")
        
        # If we have reached the end of the survey, end the survey
        if current_index >= len(survey.get("questions", [])):
            twiml = twilio_connector.generate_end_survey_twiml(survey.get("outro_message", "Thank you!"))
            now = datetime.utcnow()
            duration = (now - call["started_at"]).total_seconds() if call.get("started_at") else None
            await calls_collection.update_one(
                {"twilio_call_sid": call_sid},
                {
                    "$set": {
                        "status": CallStatus.COMPLETED.value,
                        "ended_at": now,
                        "duration_seconds": duration,
                        "updated_at": now
                    },
                    "$push": {"events": CallEvent(
                        event_type="completed",
                        description="Survey completed successfully"
                    ).dict()}
                }
            )
            return Response(content=twiml, media_type="application/xml")
        
        question = survey["questions"][current_index]
        response_value = speech_result if speech_result else digits
        
        logger.info(f"Processing response '{response_value}' for question {current_index}: {question.get('text', 'N/A')}")
        
        results_collection = MongoDB.get_collection("survey_results")
        result = await results_collection.find_one({
            "call_id": str(call["_id"]),
            "survey_id": survey_id_str
        })
        if result:
            await results_collection.update_one(
                {"_id": result["_id"]},
                {"$set": {f"responses.{question['id']}": response_value}}
            )
        else:
            from ..models.survey import SurveyResult
            result_doc = SurveyResult(
                survey_id=survey_id_str,
                call_id=str(call["_id"]),
                contact_phone_number=call.get("phone_number"),
                start_time=call.get("started_at", datetime.utcnow()),
                responses={question["id"]: response_value}
            )
            result_id = await results_collection.insert_one(result_doc.dict(by_alias=True))
            await calls_collection.update_one(
                {"_id": call["_id"]},
                {"$set": {"survey_result_id": str(result_id.inserted_id)}}
            )
        
        from ..services.llm.orchestrator import LLMOrchestrator
        llm_orchestrator = LLMOrchestrator()
        logger.info(f"About to analyze response: {response_value}")
        
        # ULTRA-SIMPLE: Skip all LLM processing for now
        logger.info("SKIPPING LLM ANALYSIS - Using simple progression")
        analysis_result = {"condition": "neutral", "sentiment": "neutral"}
        
        # Simple conversation history update
        conversation_history = call.get("metadata", {}).get("conversation_history", [])
        conversation_history.append({
            "question": question.get("text", ""),
            "response": response_value,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Simple progression: just go to next question
        current_index += 1
        
        if current_index >= len(survey.get("questions", [])):
            logger.info("Survey completed, generating end survey TwiML")
            twiml = twilio_connector.generate_end_survey_twiml(survey.get("outro_message", "Thank you!"))
            await calls_collection.update_one(
                {"twilio_call_sid": call_sid},
                {
                    "$set": {
                        "metadata.current_question_index": current_index,
                        "metadata.conversation_history": conversation_history,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return Response(content=twiml, media_type="application/xml")
        
        next_question = survey["questions"][current_index]
        logger.info(f"Generating question prompt for: {next_question.get('text', 'N/A')}")
        
        # Generate AI-enhanced question with fallback handling
        try:
            ai_response = await llm_orchestrator.generate_question_prompt(
                question=next_question,
                survey=survey,
                conversation_history=conversation_history
            )
            logger.info(f"AI response generated: {ai_response}")
        except Exception as ai_error:
            logger.warning(f"AI generation failed, using fallback: {ai_error}")
            # Graceful fallback to simple question text
            ai_response = {
                "text": next_question.get("text", "Please tell me your thoughts on this topic."),
                "metadata": {"fallback": True}
            }
        
        conversation_history.append({
            "is_ai": True,
            "text": ai_response["text"],
            "timestamp": datetime.utcnow().isoformat()
        })
        await calls_collection.update_one(
            {"twilio_call_sid": call_sid},
            {
                "$set": {
                    "metadata.current_question_index": current_index,
                    "metadata.conversation_history": conversation_history,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Generating TwiML for question type: {next_question['question_type']}")
        twiml = twilio_connector.generate_question_twiml(
            ai_response["text"],
            question_type=next_question["question_type"],
            options=next_question.get("options", [])
        )
        logger.info(f"TwiML generated successfully")
        return Response(content=twiml, media_type="application/xml")
    
    except Exception as e:
        logger.error(f"Error in gather webhook: {str(e)}", exc_info=True)
        twilio_connector = TwilioConnector()
        twiml = twilio_connector.generate_error_twiml("An unexpected error occurred.")
        return Response(content=twiml, media_type="application/xml")
    

@router.post("/status-callback", status_code=status.HTTP_200_OK)
async def twilio_status_callback(form_data: Dict[str, Any] = Depends(validate_twilio_signature_disabled)):
    """
    Webhook for Twilio call status updates.
    This is called when a call's status changes (ringing, in-progress, completed, etc.)
    """
    try:
        call_sid = form_data.get("CallSid")
        call_status = form_data.get("CallStatus")
        
        logger.info(f"Received status callback for call {call_sid}: {call_status}")
        
        # Map Twilio call status to our call status
        status_mapping = {
            "queued": CallStatus.SCHEDULED,
            "ringing": CallStatus.SCHEDULED,
            "in-progress": CallStatus.IN_PROGRESS,
            "completed": CallStatus.COMPLETED,
            "busy": CallStatus.FAILED,
            "no-answer": CallStatus.FAILED,
            "canceled": CallStatus.CANCELLED,
            "failed": CallStatus.FAILED
        }
        
        our_status = status_mapping.get(call_status.lower())
        if not our_status:
            logger.warning(f"Unknown call status: {call_status}")
            return JSONResponse({"status": "acknowledged", "message": "Unknown call status"})
        
        # Update call in database
        calls_collection = MongoDB.get_collection("calls")
        call = await calls_collection.find_one({"twilio_call_sid": call_sid})
        
        if not call:
            logger.warning(f"Call not found for SID: {call_sid}")
            return JSONResponse({"status": "error", "message": "Call not found"})
        
        # Create event for status change
        event = CallEvent(
            event_type=f"status_changed",
            description=f"Twilio status changed to {call_status}"
        )
        
        # Update fields based on status
        update_data = {
            "status": our_status.value,
            "updated_at": datetime.utcnow()
        }
        
        # Add additional fields based on status
        if our_status == CallStatus.IN_PROGRESS and not call.get("started_at"):
            update_data["started_at"] = datetime.utcnow()
        
        if our_status in [CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.CANCELLED]:
            update_data["ended_at"] = datetime.utcnow()
            
            # Calculate duration if call was started
            if call.get("started_at"):
                duration = (datetime.utcnow() - call["started_at"]).total_seconds()
                update_data["duration_seconds"] = duration
        
        # Update call
        await calls_collection.update_one(
            {"twilio_call_sid": call_sid},
            {
                "$set": update_data,
                "$push": {"events": event.dict()}
            }
        )
        
        return JSONResponse({"status": "success", "message": "Call status updated"})
    
    except Exception as e:
        logger.error(f"Error in status callback: {str(e)}", exc_info=True)
        return JSONResponse(
            {"status": "error", "message": "An unexpected error occurred"},
            status_code=500
        )

@router.post("/recording-callback", status_code=status.HTTP_200_OK)
async def twilio_recording_callback(form_data: Dict[str, Any] = Depends(validate_twilio_signature_disabled)):
    """
    Webhook for Twilio recording notifications.
    This is called when a recording is available.
    """
    try:
        call_sid = form_data.get("CallSid")
        recording_sid = form_data.get("RecordingSid")
        recording_url = form_data.get("RecordingUrl")
        recording_duration = form_data.get("RecordingDuration")
        recording_status = form_data.get("RecordingStatus")
        
        logger.info(f"Received recording callback for call {call_sid}: {recording_sid} with status {recording_status}")
        
        # Update call in database
        calls_collection = MongoDB.get_collection("calls")
        
        # Recording metadata
        recording_info = {
            "sid": recording_sid,
            "url": recording_url,
            "duration": recording_duration,
            "status": recording_status,
            "received_at": datetime.utcnow().isoformat()
        }
        
        # Only transcribe if the recording is completed
        if recording_status == "completed":
            # Make the recording URL accessible (add .mp3 extension for direct download)
            download_url = recording_url
            if not download_url.endswith(".mp3"):
                download_url = f"{download_url}.mp3"
            
            # Initialize STT service
            from ..services.telephony.speech_to_text import STTService
            stt_service = STTService()
            
            try:
                # Transcribe the recording
                transcription_result = await stt_service.transcribe_audio(
                    audio_source=download_url,
                    audio_format="mp3",
                    sample_rate=8000,  # Twilio typically uses 8kHz
                    channels=1
                )
                
                # Add transcription to recording info
                recording_info["transcription"] = transcription_result
                
                logger.info(f"Successfully transcribed recording {recording_sid}")
                
                # Add an event for the transcription
                await calls_collection.update_one(
                    {"twilio_call_sid": call_sid},
                    {
                        "$push": {"events": CallEvent(
                            event_type="transcription_completed",
                            description="Call recording transcribed successfully"
                        ).dict()}
                    }
                )
            except Exception as e:
                logger.error(f"Failed to transcribe recording: {str(e)}", exc_info=True)
                recording_info["transcription_error"] = str(e)
        
        # Update call with recording info
        await calls_collection.update_one(
            {"twilio_call_sid": call_sid},
            {
                "$set": {
                    "metadata.recording": recording_info,
                    "updated_at": datetime.utcnow()
                },
                "$push": {"events": CallEvent(
                    event_type="recording_received",
                    description=f"Recording received with status: {recording_status}"
                ).dict()}
            }
        )
        
        return JSONResponse({
            "status": "success", 
            "message": "Recording information saved",
            "transcription_status": "completed" if recording_info.get("transcription") else "not_available"
        })
    
    except Exception as e:
        logger.error(f"Error in recording callback: {str(e)}", exc_info=True)
        return JSONResponse(
            {"status": "error", "message": "An unexpected error occurred"},
            status_code=500
        )