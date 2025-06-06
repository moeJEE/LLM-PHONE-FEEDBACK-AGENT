from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId
from ..services.telephony.twilio_connector import TwilioConnector
from ..core.config import get_settings

settings = get_settings()

from ..core.security import get_current_user, ClerkUser
from ..core.logging import get_logger
from ..db.mongodb import MongoDB
from ..models.call import (
    CallCreate, 
    CallUpdate, 
    CallResponse, 
    CallDB,
    CallStatus,
    CallEvent,
    CallDirection,
    CallPriority,
    CallStats
)
from ..services.whatsapp_service import whatsapp_service
from ..services.nexmo_whatsapp_service import NexmoWhatsAppService
from ..models.survey import SurveyResult

logger = get_logger("api.calls")
router = APIRouter()

# Initialize Nexmo WhatsApp service
nexmo_whatsapp_service = NexmoWhatsAppService()

# Helper function to convert MongoDB document to Pydantic model
def convert_call_doc(call_doc):
    if not call_doc:
        return None
    
    # Create a copy to avoid modifying the original
    call_doc = call_doc.copy()
    call_doc["id"] = str(call_doc.pop("_id"))
    
    # Fix common status format issues
    if "status" in call_doc:
        status_value = call_doc["status"]
        # Common status fixes
        status_mapping = {
            'in_progress': 'in-progress',
            'inprogress': 'in-progress',
            'in progress': 'in-progress',
            'active': 'in-progress',
            'running': 'in-progress',
            'finished': 'completed',
            'done': 'completed',
            'error': 'failed',
            'canceled': 'cancelled',
        }
        
        if status_value in status_mapping:
            call_doc["status"] = status_mapping[status_value]
            print(f"[DEBUG] Fixed status: '{status_value}' -> '{call_doc['status']}'")
    
    # Convert datetime strings back to datetime objects if needed
    datetime_fields = ["scheduled_time", "started_at", "ended_at", "created_at", "updated_at"]
    for field in datetime_fields:
        if field in call_doc and call_doc[field] and isinstance(call_doc[field], str):
            try:
                call_doc[field] = datetime.fromisoformat(call_doc[field])
            except ValueError:
                # Keep as string if conversion fails
                pass
    
    # Convert event timestamps
    if "events" in call_doc and call_doc["events"]:
        for event in call_doc["events"]:
            if "timestamp" in event and isinstance(event["timestamp"], str):
                try:
                    event["timestamp"] = datetime.fromisoformat(event["timestamp"])
                except ValueError:
                    pass
    
    try:
        return CallResponse(**call_doc)
    except Exception as e:
        print(f"[ERROR] Failed to convert call doc: {e}")
        print(f"[ERROR] Call doc: {call_doc}")
        # Try to fix and retry
        if "status" in call_doc:
            print(f"[ERROR] Problematic status: '{call_doc['status']}'")
            # Fallback to a valid status
            call_doc["status"] = "scheduled"
            print(f"[ERROR] Fallback to status: 'scheduled'")
            try:
                return CallResponse(**call_doc)
            except Exception as e2:
                print(f"[ERROR] Even fallback failed: {e2}")
                raise e
        raise e

# Helper function to check survey exists
async def check_survey_exists(survey_id: str, user_id: str = None):
    """Check if survey exists and belongs to user"""
    surveys_collection = MongoDB.get_collection("surveys")
    
    if not ObjectId.is_valid(survey_id):
        return None
    
    survey = await surveys_collection.find_one({
        "_id": ObjectId(survey_id),
        "owner_id": user_id
    })
    
    return survey

# Helper function to build query with auth bypass
def build_call_query(user_id: str = None, extra_filters: dict = None):
    """Build query for calls with proper user filtering"""
    query = {}
    
    # Always filter by user_id for proper security
    if user_id:
        query["owner_id"] = user_id
    
    if extra_filters:
        query.update(extra_filters)
    
    return query

# Endpoints
@router.post("/", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def create_call(
    call: CallCreate, 
    current_user: ClerkUser = Depends(get_current_user),
    send_whatsapp_survey: bool = Query(False, description="Send WhatsApp survey immediately"),
    knowledge_base_only: bool = Query(False, description="Use knowledge base only without survey")
):
    """Schedule a new call with optional immediate WhatsApp survey or knowledge base only interaction"""
    
    survey = None
    
    # If knowledge_base_only mode, we don't need a survey
    if not knowledge_base_only:
        # Check if survey exists only when not in knowledge_base_only mode
        survey = await check_survey_exists(call.survey_id, current_user.id)
        
        if not survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Survey not found"
            )
    else:
        # For knowledge base only, we need to ensure knowledge_base_id is provided
        if not call.metadata or not call.metadata.get("knowledge_base_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="knowledge_base_id is required in metadata for knowledge base only calls"
            )
    
    # Create initial event
    event_description = f"Call scheduled for {call.scheduled_time}"
    if knowledge_base_only:
        event_description += " (Knowledge Base only)"
    
    initial_event = CallEvent(
        event_type="scheduled",
        description=event_description
    )
    
    # Create call object with user info
    call_db = CallDB(
        **call.dict(),
        owner_id=current_user.id,
        events=[initial_event]
    )
    
    # Add knowledge_base_only flag to metadata
    if knowledge_base_only:
        if not call_db.metadata:
            call_db.metadata = {}
        call_db.metadata["knowledge_base_only"] = True
        call_db.metadata["call_type"] = "knowledge_base_inquiry"
    
    # Insert into database
    calls_collection = MongoDB.get_collection("calls")
    result = await calls_collection.insert_one(call_db.dict(by_alias=True))
    
    # Get created call
    created_call = await calls_collection.find_one({"_id": result.inserted_id})
    call_id = str(result.inserted_id)
    
    # Send WhatsApp interaction if requested
    if send_whatsapp_survey:
        try:
            if knowledge_base_only:
                # Clear any pending surveys before sending knowledge base inquiry
                await clear_pending_surveys_for_phone(call.phone_number, "Knowledge Base inquiry call initiated")
                
                # Send knowledge base inquiry via WhatsApp
                await send_whatsapp_knowledge_inquiry(call_id, current_user.id, call.metadata.get("knowledge_base_id"), created_call)
                event_description = f"WhatsApp knowledge inquiry sent to {call.phone_number}"
                event_type = "whatsapp_knowledge_inquiry_sent"
            else:
                # Send regular survey
                await send_whatsapp_survey_internal(call_id, current_user.id, survey, created_call)
                event_description = f"WhatsApp survey sent to {call.phone_number}"
                event_type = "whatsapp_survey_sent"
            
            # Add event for WhatsApp interaction sent
            whatsapp_event = CallEvent(
                event_type=event_type,
                description=event_description
            )
            
            await calls_collection.update_one(
                {"_id": result.inserted_id},
                {
                    "$push": {"events": whatsapp_event.dict()},
                    "$set": {
                        "updated_at": datetime.utcnow(),
                        "metadata": {
                            **created_call.get("metadata", {}),
                            f"whatsapp_{('knowledge_inquiry' if knowledge_base_only else 'survey')}_sent": True,
                            f"whatsapp_{('knowledge_inquiry' if knowledge_base_only else 'survey')}_time": datetime.utcnow().isoformat()
                        }
                    }
                }
            )
            
            # Re-fetch updated call
            created_call = await calls_collection.find_one({"_id": result.inserted_id})
            
        except Exception as e:
            interaction_type = "knowledge inquiry" if knowledge_base_only else "survey"
            logger.error(f"Failed to send WhatsApp {interaction_type} for call {call_id}: {e}")
            # Don't fail the call creation, just log the error
    
    call_type = "knowledge base inquiry" if knowledge_base_only else "survey call"
    logger.info(f"{call_type.title()} scheduled with ID: {result.inserted_id}", 
                extra={"user_id": current_user.id, "phone_number": call.phone_number})
    
    return convert_call_doc(created_call)

@router.get("/", response_model=List[CallResponse])
async def get_calls(
    status: Optional[str] = Query(None, description="Filter by call status"),
    survey_id: Optional[str] = Query(None, description="Filter by survey ID"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    skip: int = Query(0, ge=0, description="Number of calls to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of calls to return"),
    current_user: ClerkUser = Depends(get_current_user)
):
    """Get all calls with optional filters"""
    
    calls_collection = MongoDB.get_collection("calls")
    
    # Build base query with user filtering
    query = build_call_query(current_user.id)
    
    # Add filters
    if status:
        query["status"] = status
        
    if survey_id:
        if ObjectId.is_valid(survey_id):
            query["survey_id"] = survey_id
        else:
            # Invalid survey_id format, return empty result
            return []
    
    # Date range filter
    if start_date or end_date:
        date_filter = {}
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                date_filter["$gte"] = start_dt
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                )
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                date_filter["$lte"] = end_dt
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                )
        
        query["scheduled_time"] = date_filter
    
    # Get calls with pagination
    cursor = calls_collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
    calls = await cursor.to_list(length=limit)
    
    # Convert to response models
    call_responses = []
    for call_doc in calls:
        try:
            converted = convert_call_doc(call_doc)
            if converted:
                call_responses.append(converted)
        except Exception as e:
            logger.error(f"Error converting call document: {e}", extra={"call_id": str(call_doc.get('_id'))})
            continue
    
    logger.info(f"Retrieved {len(call_responses)} calls", 
                extra={"user_id": current_user.id, "filters": {"status": status, "survey_id": survey_id}})
    
    return call_responses

@router.get("/{call_id}", response_model=CallResponse)
async def get_call(call_id: str, current_user: ClerkUser = Depends(get_current_user)):
    """Get a specific call by ID"""
    
    calls_collection = MongoDB.get_collection("calls")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(call_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID format"
        )
    
    # Find call with user filtering
    query = build_call_query(current_user.id, {"_id": ObjectId(call_id)})
    call = await calls_collection.find_one(query)
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    return convert_call_doc(call)

@router.put("/{call_id}", response_model=CallResponse)
async def update_call(
    call_id: str,
    call_update: CallUpdate,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Update a call"""
    calls_collection = MongoDB.get_collection("calls")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(call_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID format"
        )
    
    # Find call
    existing_call = await calls_collection.find_one({
        "_id": ObjectId(call_id),
        "owner_id": current_user.id
    })
    
    if not existing_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Check if call is in a state that can be updated
    current_status = existing_call["status"]
    new_status = call_update.status
    
    # Define allowed status transitions
    allowed_updates = [
        CallStatus.SCHEDULED.value, 
        CallStatus.FAILED.value
    ]
    
    # Allow specific status transitions for pause/resume functionality
    if current_status == CallStatus.IN_PROGRESS.value and new_status == CallStatus.PAUSED.value:
        # Allow pausing an in-progress call
        pass
    elif current_status == CallStatus.PAUSED.value and new_status == CallStatus.IN_PROGRESS.value:
        # Allow resuming a paused call
        pass
    elif current_status == CallStatus.IN_PROGRESS.value and new_status == CallStatus.COMPLETED.value:
        # Allow ending an in-progress call
        pass
    elif current_status not in allowed_updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update call in {current_status} status"
        )
    
    # Remove None values from update
    update_data = {k: v for k, v in call_update.dict().items() if v is not None}
    
    # Always update the updated_at timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    # Add event for status change if applicable
    if "status" in update_data and update_data["status"] != existing_call["status"]:
        event = CallEvent(
            event_type=f"status_changed",
            description=f"Status changed from {existing_call['status']} to {update_data['status']}"
        )
        update_data["events"] = existing_call["events"] + [event.dict()]
    
    # Update call
    await calls_collection.update_one(
        {"_id": ObjectId(call_id)},
        {"$set": update_data}
    )
    
    # Get updated call
    updated_call = await calls_collection.find_one({"_id": ObjectId(call_id)})
    
    logger.info(f"Call updated with ID: {call_id}", extra={"user_id": current_user.id})
    
    return convert_call_doc(updated_call)

@router.delete("/{call_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_call(
    call_id: str,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Delete a call"""
    calls_collection = MongoDB.get_collection("calls")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(call_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID format"
        )
    
    # Check if call exists and belongs to user
    existing_call = await calls_collection.find_one({
        "_id": ObjectId(call_id),
        "owner_id": current_user.id
    })
    
    if not existing_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Check if call can be deleted
    if existing_call["status"] in [CallStatus.IN_PROGRESS.value, CallStatus.PAUSED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an active call"
        )
    
    # Delete call
    await calls_collection.delete_one({"_id": ObjectId(call_id)})
    
    logger.info(f"Call deleted with ID: {call_id}", extra={"user_id": current_user.id})

@router.post("/{call_id}/cancel", response_model=CallResponse)
async def cancel_call(
    call_id: str,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Cancel a scheduled call"""
    calls_collection = MongoDB.get_collection("calls")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(call_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID format"
        )
    
    # Find call
    existing_call = await calls_collection.find_one({
        "_id": ObjectId(call_id),
        "owner_id": current_user.id
    })
    
    if not existing_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Check if call can be cancelled
    if existing_call["status"] != CallStatus.SCHEDULED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel call in {existing_call['status']} status"
        )
    
    # Create cancel event
    cancel_event = CallEvent(
        event_type="cancelled",
        description="Call cancelled by user"
    )
    
    # Update call status
    await calls_collection.update_one(
        {"_id": ObjectId(call_id)},
        {
            "$set": {
                "status": CallStatus.CANCELLED.value,
                "updated_at": datetime.utcnow()
            },
            "$push": {"events": cancel_event.dict()}
        }
    )
    
    # Get updated call
    updated_call = await calls_collection.find_one({"_id": ObjectId(call_id)})
    
    logger.info(f"Call cancelled with ID: {call_id}", extra={"user_id": current_user.id})
    
    return convert_call_doc(updated_call)

@router.post("/{call_id}/start", response_model=CallResponse)
async def start_call(call_id: str, current_user: ClerkUser = Depends(get_current_user)):
    """Start a scheduled survey interaction immediately by sending an initial WhatsApp message."""
    
    calls_collection = MongoDB.get_collection("calls")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(call_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID format"
        )
    
    # Find call in the database with proper user filtering
    query = build_call_query(current_user.id, {"_id": ObjectId(call_id)})
    existing_call = await calls_collection.find_one(query)
    
    if not existing_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call record not found"
        )
    
    # Check if call is in SCHEDULED status and can be started
    if existing_call["status"] != CallStatus.SCHEDULED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start survey in {existing_call['status']} status"
        )
    
    # Verify that the call record contains a phone number to message
    if "phone_number" not in existing_call:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call record is missing phone number for WhatsApp"
        )
    
    try:
        # Prepare parameters for the WhatsApp template
        # The ContentSID HXb5b62575e6e4ff6129ad7c8efe1f983e corresponds to:
        # "Your appointment is coming up on {{1}} at {{2}}. If you need to change it, please reply back and let us know."
        # We need to map survey-relevant info to {{1}} and {{2}}.
        # For example, {{1}} could be the survey name, and {{2}} a brief instruction.
        call_metadata = existing_call.get("metadata", {})
        survey_name = call_metadata.get("survey_name", existing_call.get("survey_id", "our survey")) # Fallback to survey_id
        initial_prompt = call_metadata.get("initial_prompt", "Please reply to start.") # Example prompt

        # Use the send_appointment_reminder as it's configured for the specific ContentSID
        # The 'appointment_date' field maps to {{1}} and 'appointment_time' to {{2}}
        whatsapp_response = whatsapp_service.send_appointment_reminder(
            to_number=existing_call["phone_number"],
            appointment_date=survey_name,  # This will be {{1}} in the template
            appointment_time=initial_prompt, # This will be {{2}} in the template
            survey_id=existing_call["survey_id"],
            call_id=call_id
        )
        
        logger.info(f"WhatsApp survey initiation response for call {call_id}: {whatsapp_response}")

        if not whatsapp_response.get("success"):
            error_detail = whatsapp_response.get('error', 'Unknown WhatsApp service error')
            logger.error(f"WhatsApp service failed to send message for call {call_id}: {error_detail}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error sending WhatsApp initiation message: {error_detail}"
            )

    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Error initiating survey via WhatsApp for call {call_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error initiating survey via WhatsApp."
        )
    
    now = datetime.utcnow()
    
    # Update call document: set status, record start time and store the WhatsApp message SID
    update_data = {
        "$set": {
            "status": CallStatus.IN_PROGRESS.value, # This status might need adjustment for WhatsApp flow (e.g., AWAITING_USER_REPLY)
            "started_at": now,
            "updated_at": now,
            "metadata": {
                **existing_call.get("metadata", {}), # Preserve existing metadata
                "whatsapp_message_sid": whatsapp_response.get("message_sid"),
                "whatsapp_initiation_status": whatsapp_response.get("status"), # More specific key
                "whatsapp_template_param1": survey_name,
                "whatsapp_template_param2": initial_prompt,
                "communication_type": "whatsapp" # Mark as WhatsApp communication
            }
        },
        "$push": {"events": CallEvent(
            event_type="survey_initiated_whatsapp",
            description=f"Survey initiated via WhatsApp to {existing_call['phone_number']} using template. Param1='{survey_name}', Param2='{initial_prompt}'."
        ).dict()}
    }
    
    # For backward compatibility, if twilio_call_sid is used generically for message SIDs
    if whatsapp_response.get("success") and whatsapp_response.get("message_sid"):
        update_data["$set"]["twilio_call_sid"] = whatsapp_response.get("message_sid") # Using message_sid here
    
    await calls_collection.update_one(
        {"_id": ObjectId(call_id)},
        update_data
    )
    
    # Retrieve updated call document
    updated_call = await calls_collection.find_one({"_id": ObjectId(call_id)})
    
    logger.info(f"Survey interaction initiated via WhatsApp for call ID: {call_id}", extra={"user_id": current_user.id})
    
    return convert_call_doc(updated_call)

@router.post("/{call_id}/send-whatsapp", response_model=CallResponse)
async def send_whatsapp_reminder(
    call_id: str,
    current_user: ClerkUser = Depends(get_current_user),
    appointment_date: str = "12/1",
    appointment_time: str = "3pm"
):
    """Send a WhatsApp appointment reminder for a scheduled call."""
    
    calls_collection = MongoDB.get_collection("calls")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(call_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID format"
        )
    
    # Find call in the database with proper user filtering
    query = build_call_query(current_user.id, {"_id": ObjectId(call_id)})
    existing_call = await calls_collection.find_one(query)
    
    if not existing_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Verify that the call record contains a phone number
    if "phone_number" not in existing_call:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call record is missing phone number"
        )
    
    try:
        # Send WhatsApp appointment reminder using the pre-approved template
        whatsapp_response = whatsapp_service.send_appointment_reminder(
            to_number=existing_call["phone_number"],
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            survey_id=existing_call["survey_id"],
            call_id=call_id
        )
        
        logger.info(f"WhatsApp reminder sent: {whatsapp_response}")
        
        if not whatsapp_response.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"WhatsApp service error: {whatsapp_response.get('error', 'Unknown error')}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending WhatsApp appointment reminder: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending WhatsApp appointment reminder."
        )
    
    now = datetime.utcnow()
    
    # Update call document with WhatsApp message information
    update_data = {
        "$set": {
            "updated_at": now,
            "metadata": {
                **existing_call.get("metadata", {}),
                "whatsapp_message_sid": whatsapp_response.get("message_sid"),
                "whatsapp_status": whatsapp_response.get("status"),
                "appointment_date": appointment_date,
                "appointment_time": appointment_time
            }
        },
        "$push": {"events": CallEvent(
            event_type="whatsapp_reminder_sent",
            description=f"WhatsApp appointment reminder sent to {existing_call['phone_number']} for {appointment_date} at {appointment_time}"
        ).dict()}
    }
    
    await calls_collection.update_one(
        {"_id": ObjectId(call_id)},
        update_data
    )
    
    # Retrieve updated call document
    updated_call = await calls_collection.find_one({"_id": ObjectId(call_id)})
    
    logger.info(f"WhatsApp appointment reminder sent for call ID: {call_id}", extra={"user_id": current_user.id})
    
    return convert_call_doc(updated_call)

@router.get("/stats/summary", response_model=CallStats)
async def get_call_stats(
    period: str = Query("all", description="Stats period: 'today', 'week', 'month', 'all'"),
    current_user: ClerkUser = Depends(get_current_user)
):
    """Get call statistics summary"""
    
    calls_collection = MongoDB.get_collection("calls")
    
    # Calculate date range based on period
    now = datetime.utcnow()
    date_filter = {}
    
    if period == "today":
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        date_filter = {"created_at": {"$gte": start_of_day}}
    elif period == "week":
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        date_filter = {"created_at": {"$gte": start_of_week}}
    elif period == "month":
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        date_filter = {"created_at": {"$gte": start_of_month}}
    # "all" period means no date filter
    
    # Build base query with user filtering
    base_query = build_call_query(current_user.id, date_filter)
    
    # Get total calls
    total_calls = await calls_collection.count_documents(base_query)
    
    # Get calls by status
    scheduled_calls = await calls_collection.count_documents({
        **base_query,
        "status": CallStatus.SCHEDULED.value
    })
    
    in_progress_calls = await calls_collection.count_documents({
        **base_query,
        "status": CallStatus.IN_PROGRESS.value
    })
    
    completed_calls = await calls_collection.count_documents({
        **base_query,
        "status": CallStatus.COMPLETED.value
    })
    
    failed_calls = await calls_collection.count_documents({
        **base_query,
        "status": CallStatus.FAILED.value
    })
    
    cancelled_calls = await calls_collection.count_documents({
        **base_query,
        "status": CallStatus.CANCELLED.value
    })
    
    # Calculate average duration for completed calls using survey_results data
    survey_results_collection = MongoDB.get_collection("survey_results")
    
    # Simple approach: get all calls for this user first
    user_calls = await calls_collection.find({"owner_id": current_user.id}).to_list(length=None)
    user_call_ids = [str(call["_id"]) for call in user_calls]
    
    # Get survey results with duration for these calls
    survey_results = await survey_results_collection.find({
        "call_id": {"$in": user_call_ids},
        "duration_seconds": {"$exists": True, "$ne": None, "$gt": 0}
    }).to_list(length=None)
    
    # Calculate average duration
    if survey_results:
        total_duration = sum(result["duration_seconds"] for result in survey_results)
        avg_duration_seconds = total_duration / len(survey_results)
        total_duration_seconds = total_duration
        print(f"DEBUG: Found {len(survey_results)} survey results with duration for user {current_user.id}")
        print(f"DEBUG: Total duration: {total_duration}, Average: {avg_duration_seconds}")
    else:
        avg_duration_seconds = 0
        total_duration_seconds = 0
        print(f"DEBUG: No survey results with duration found for user {current_user.id}")
        print(f"DEBUG: User has {len(user_call_ids)} calls: {user_call_ids[:3]}...")  # Show first 3
    
    logger.info(f"Retrieved call stats for period '{period}'", 
                extra={"user_id": current_user.id, "total_calls": total_calls})
    
    return CallStats(
        total_calls=total_calls,
        scheduled_calls=scheduled_calls,
        in_progress_calls=in_progress_calls,
        completed_calls=completed_calls,
        failed_calls=failed_calls,
        cancelled_calls=cancelled_calls,
        average_duration_seconds=avg_duration_seconds,
        total_duration_seconds=total_duration_seconds
    )

@router.post("/{call_id}/send-whatsapp-survey", response_model=CallResponse)
async def send_whatsapp_survey(
    call_id: str,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Send a WhatsApp survey for an existing call"""
    
    calls_collection = MongoDB.get_collection("calls")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(call_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID format"
        )
    
    # Find call in the database
    query = build_call_query(current_user.id, {"_id": ObjectId(call_id)})
    existing_call = await calls_collection.find_one(query)
    
    if not existing_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Get survey
    survey = await check_survey_exists(existing_call["survey_id"], current_user.id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey associated with this call not found"
        )
    
    try:
        await send_whatsapp_survey_internal(call_id, current_user.id, survey, existing_call)
        
        # Update call with WhatsApp survey event
        whatsapp_event = CallEvent(
            event_type="whatsapp_survey_sent",
            description=f"WhatsApp survey sent to {existing_call['phone_number']}"
        )
        
        update_data = {
            "$push": {"events": whatsapp_event.dict()},
            "$set": {
                "updated_at": datetime.utcnow(),
                "metadata": {
                    **existing_call.get("metadata", {}),
                    "whatsapp_survey_sent": True,
                    "whatsapp_survey_time": datetime.utcnow().isoformat()
                }
            }
        }
        
        await calls_collection.update_one(
            {"_id": ObjectId(call_id)},
            update_data
        )
        
        # Get updated call
        updated_call = await calls_collection.find_one({"_id": ObjectId(call_id)})
        
        logger.info(f"WhatsApp survey sent for call ID: {call_id}", extra={"user_id": current_user.id})
        
        return convert_call_doc(updated_call)
        
    except Exception as e:
        logger.error(f"Error sending WhatsApp survey: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send WhatsApp survey: {str(e)}"
        )

async def send_whatsapp_survey_internal(call_id: str, user_id: str, survey: dict, call_doc: dict = None):
    """Internal function to send WhatsApp survey"""
    
    if not call_doc:
        calls_collection = MongoDB.get_collection("calls")
        call_doc = await calls_collection.find_one({"_id": ObjectId(call_id)})
    
    phone_number = call_doc["phone_number"]
    
    # Create survey result record
    survey_result = SurveyResult(
        survey_id=survey["_id"] if isinstance(survey["_id"], str) else str(survey["_id"]),
        call_id=call_id,
        contact_phone_number=phone_number,
        start_time=datetime.utcnow(),
        completed=False,
        responses={},
        sentiment_scores={},
        overall_sentiment=None
    )
    
    # Store survey result
    results_collection = MongoDB.get_collection("survey_results")
    result = await results_collection.insert_one(survey_result.dict(by_alias=True))
    survey_result_id = str(result.inserted_id)
    
    # Prepare WhatsApp message
    first_question = survey["questions"][0] if survey["questions"] else None
    
    if not first_question:
        raise Exception("Survey has no questions")
    
    # Get survey title and description for context
    survey_title = survey.get("title", "Survey")
    survey_description = survey.get("description", "")
    
    # Create survey-focused message
    message = f"""📋 Hello! Thank you for your interest in our services.

We'd like to ask you a few questions to better understand your experience and needs."""
    
    # Add survey context if available
    if survey_title and survey_title != "Survey":
        message += f"\n\nSurvey: {survey_title}"
    
    if survey_description:
        message += f"\n{survey_description}"
    
    # Add the first question
    question_text = first_question.get('text', 'How would you rate our service?')
    message += f"""

Question 1: {question_text}"""
    
    # Add response instructions based on question type
    question_type = first_question.get('type', 'text')
    if question_type == 'multiple_choice' and first_question.get('options'):
        options = first_question['options']
        options_text = "\n".join([f"{i+1}. {option}" for i, option in enumerate(options)])
        message += f"""

Please choose from the following options:
{options_text}

Reply with the NUMBER (1, 2, 3, etc.) or the EXACT TEXT of your choice."""
    elif question_type == 'rating':
        scale_min = first_question.get('scale_min', 1)
        scale_max = first_question.get('scale_max', 10)
        message += f"""

Please rate on a scale of {scale_min} to {scale_max} (where {scale_max} is the highest).

Reply with a NUMBER between {scale_min} and {scale_max}."""
    elif question_type in ['yes_no', 'boolean']:
        message += """

Please answer with "Yes" or "No"."""
    elif question_type == 'scale':
        scale_min = first_question.get('scale_min', 1)
        scale_max = first_question.get('scale_max', 5)
        scale_labels = first_question.get('scale_labels', {})
        message += f"""

Please rate on a scale of {scale_min} to {scale_max}"""
        if scale_labels:
            if str(scale_min) in scale_labels:
                message += f" (where {scale_min} = {scale_labels[str(scale_min)]}"
            if str(scale_max) in scale_labels:
                message += f" and {scale_max} = {scale_labels[str(scale_max)]}"
            message += ")"
        message += f"""

Reply with a NUMBER between {scale_min} and {scale_max}."""
    elif question_type in ['number', 'numeric']:
        min_val = first_question.get('min_value')
        max_val = first_question.get('max_value')
        if min_val is not None and max_val is not None:
            message += f"""

Please enter a NUMBER between {min_val} and {max_val}."""
        elif min_val is not None:
            message += f"""

Please enter a NUMBER (minimum: {min_val})."""
        elif max_val is not None:
            message += f"""

Please enter a NUMBER (maximum: {max_val})."""
        else:
            message += """

Please enter a NUMBER."""
    else:  # text or any other type
        char_limit = first_question.get('max_length')
        if char_limit:
            message += f"""

Please reply with your answer (maximum {char_limit} characters)."""
        else:
            message += """

Reply with your answer."""
    
    full_message = message
    full_message += f"\n\n_Survey ID: {survey_result_id}_"
    
    # Format phone number
    formatted_phone = phone_number
    if not formatted_phone.startswith('+'):
        formatted_phone = f"+1{formatted_phone.lstrip('+1')}"
    
    # Send WhatsApp message using Nexmo
    await nexmo_whatsapp_service.send_whatsapp_message(formatted_phone, full_message)
    
    whatsapp_event = CallEvent(
        event_type="whatsapp_survey_sent",
        description=f"WhatsApp survey sent to {phone_number}"
    )
    
    # Update call metadata, preserving existing important fields
    current_metadata = call_doc.get("metadata", {})
    updated_metadata = {
        **current_metadata,  # Preserve all existing metadata including knowledge_base_only and call_type
        "whatsapp_survey_sent": True,
        "whatsapp_survey_time": datetime.utcnow().isoformat(),
        "survey_id": survey["_id"] if isinstance(survey["_id"], str) else str(survey["_id"]),
        "survey_title": survey_title,
        "survey_result_id": survey_result_id
    }
    
    await calls_collection.update_one(
        {"_id": ObjectId(call_id)},
        {
            "$push": {"events": whatsapp_event.dict()},
            "$set": {
                "updated_at": datetime.utcnow(),
                "metadata": updated_metadata
            }
        }
    )
    
    logger.info(f"WhatsApp survey started for call {call_id}, survey result {survey_result_id}")

@router.get("/{call_id}/survey-results", response_model=List[Dict[str, Any]])
async def get_call_survey_results(
    call_id: str,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Get survey results for a specific call"""
    
    # Verify call exists and belongs to user
    calls_collection = MongoDB.get_collection("calls")
    
    if not ObjectId.is_valid(call_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call ID format"
        )
    
    query = build_call_query(current_user.id, {"_id": ObjectId(call_id)})
    existing_call = await calls_collection.find_one(query)
    
    if not existing_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Get survey results
    results_collection = MongoDB.get_collection("survey_results")
    cursor = results_collection.find({"call_id": call_id})
    results = await cursor.to_list(length=None)
    
    # Convert ObjectId to string
    for result in results:
        result["id"] = str(result.pop("_id"))
    
    return results

@router.post("/debug/add-duration-data", status_code=status.HTTP_200_OK)
async def add_duration_data_debug(
    current_user: ClerkUser = Depends(get_current_user)
):
    """Debug endpoint to add duration data to user's calls"""
    
    calls_collection = MongoDB.get_collection("calls")
    survey_results_collection = MongoDB.get_collection("survey_results")
    
    try:
        # Get user's calls
        calls_cursor = calls_collection.find({'owner_id': current_user.id})
        calls = await calls_cursor.to_list(length=None)
        
        if not calls:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No calls found for user"
            )
        
        # Check existing survey results
        call_ids = [str(call['_id']) for call in calls]
        existing_surveys = await survey_results_collection.find({
            'call_id': {'$in': call_ids}
        }).to_list(length=None)
        
        existing_call_ids = [s['call_id'] for s in existing_surveys]
        
        # Add duration data to calls that don't have survey results
        import random
        created_count = 0
        updated_count = 0
        
        for call in calls[:5]:  # Process first 5 calls
            call_id_str = str(call['_id'])
            
            if call_id_str in existing_call_ids:
                # Update existing survey result to add duration if missing
                existing_survey = next(s for s in existing_surveys if s['call_id'] == call_id_str)
                if not existing_survey.get('duration_seconds'):
                    duration = random.randint(15, 120)
                    await survey_results_collection.update_one(
                        {'_id': existing_survey['_id']},
                        {
                            '$set': {
                                'duration_seconds': duration,
                                'completed': True,
                                'updated_at': datetime.utcnow()
                            }
                        }
                    )
                    updated_count += 1
            else:
                # Create new survey result with duration
                duration = random.randint(15, 120)
                
                survey_result = {
                    'survey_id': call.get('survey_id', '507f1f77bcf86cd799439015'),  # Use actual survey_id from call
                    'call_id': call_id_str,
                    'contact_phone_number': call.get('phone_number', '+1234567890'),
                    'start_time': datetime.utcnow() - timedelta(hours=1),
                    'end_time': datetime.utcnow(),
                    'completed': True,
                    'duration_seconds': duration,
                    'responses': {
                        'satisfaction': 'Satisfied',
                        'rating': random.randint(7, 10)
                    },
                    'sentiment_scores': {
                        'overall': 0.8,
                        'satisfaction': 0.9
                    },
                    'overall_sentiment': 'positive',
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                await survey_results_collection.insert_one(survey_result)
                created_count += 1
        
        # Test the updated stats
        stats = await get_call_stats_internal(current_user)
        
        return {
            "message": f"Created {created_count} and updated {updated_count} survey results",
            "total_changes": created_count + updated_count,
            "new_average_duration": stats.get("average_duration_seconds", 0),
            "user_id": current_user.id
        }
        
    except Exception as e:
        logger.error(f"Error adding duration data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add duration data: {str(e)}"
        )

async def get_call_stats_internal(current_user):
    """Internal function to get call stats"""
    survey_results_collection = MongoDB.get_collection("survey_results")
    
    # Calculate average duration for completed calls using survey_results data
    duration_pipeline = [
        {"$addFields": {
            "call_id_obj": {
                "$cond": {
                    "if": {"$type": "$call_id"} == "string",
                    "then": {"$toObjectId": "$call_id"},
                    "else": "$call_id"
                }
            }
        }},
        {"$lookup": {
            "from": "calls",
            "localField": "call_id_obj", 
            "foreignField": "_id",
            "as": "call_info",
            "pipeline": [{"$match": {"owner_id": current_user.id}}]
        }},
        {"$match": {
            "call_info": {"$ne": []},
            "duration_seconds": {"$exists": True, "$ne": None, "$gt": 0}
        }},
        {"$group": {
            "_id": None,
            "avg_duration": {"$avg": "$duration_seconds"},
            "total_duration": {"$sum": "$duration_seconds"},
            "count": {"$sum": 1}
        }}
    ]
    
    duration_result = await survey_results_collection.aggregate(duration_pipeline).to_list(length=1)
    avg_duration_seconds = duration_result[0]["avg_duration"] if duration_result else 0
    total_duration_seconds = duration_result[0]["total_duration"] if duration_result else 0
    
    return {
        "average_duration_seconds": avg_duration_seconds,
        "total_duration_seconds": total_duration_seconds
    }

async def send_whatsapp_knowledge_inquiry(call_id: str, user_id: str, knowledge_base_id: str, call_doc: dict = None):
    """Send a WhatsApp knowledge base inquiry message"""
    try:
        # Get fresh call document from database to ensure we have the latest metadata
        calls_collection = MongoDB.get_collection("calls")
        fresh_call_doc = await calls_collection.find_one({"_id": ObjectId(call_id)})
        
        if not fresh_call_doc:
            raise HTTPException(status_code=404, detail=f"Call {call_id} not found")
        
        phone_number = fresh_call_doc.get("phone_number")
        if not phone_number:
            raise HTTPException(status_code=400, detail="Phone number not found in call")
        
        # IMPORTANT: Clear any pending surveys for this phone number to avoid confusion
        # between Knowledge Base Only calls and Survey-based calls
        await clear_pending_surveys_for_phone(phone_number, "Knowledge Base inquiry call initiated")
        
        # Get user's knowledge base documents
        knowledge_collection = MongoDB.get_collection("documents")
        
        # Check if knowledge_base_id refers to a specific document
        if knowledge_base_id and knowledge_base_id not in ["general", "default", "none"]:
            try:
                # Try to get the specific document by ID
                specific_doc = await knowledge_collection.find_one({
                    "_id": ObjectId(knowledge_base_id),
                    "owner_id": user_id,
                    "status": "processed"
                })
                
                if specific_doc:
                    kb_docs = [specific_doc]  # Use only the selected document
                    logger.info(f"🎯 Using specific document: {specific_doc.get('name', 'Unknown')}")
                else:
                    # Fallback to all documents if specific document not found
                    kb_docs = await knowledge_collection.find({
                        "owner_id": user_id,
                        "status": "processed"
                    }).to_list(length=50)
                    logger.warning(f"⚠️ Specific document {knowledge_base_id} not found, using all documents")
            except Exception as e:
                # If ObjectId conversion fails, try by name or fallback to all
                kb_docs = await knowledge_collection.find({
                    "owner_id": user_id,
                    "status": "processed"
                }).to_list(length=50)
                logger.warning(f"⚠️ Error getting specific document {knowledge_base_id}: {e}, using all documents")
        else:
            # General knowledge base - use all documents
            kb_docs = await knowledge_collection.find({
                "owner_id": user_id,
                "status": "processed"
            }).to_list(length=50)
            logger.info(f"🌐 Using general knowledge base with all documents")
        
        if not kb_docs:
            raise HTTPException(
                status_code=404,
                detail="No processed knowledge base documents found"
            )
        
        # Create document list for message
        doc_names = [doc.get("name", "Unknown") for doc in kb_docs[:5]]
        
        # Prepare different messages based on whether it's a specific document or general
        if len(kb_docs) == 1:
            # Single document - be specific
            doc_name = doc_names[0]
            message = f"""🤖 Hello! I'm here to help you with questions about {doc_name}.

📚 I have detailed information about this product/service and can answer questions about:
• Product specifications and features
• Usage instructions and benefits  
• Troubleshooting and support
• Pricing and availability
• Technical details

💬 What would you like to know about {doc_name}?

Reply to this message with your question and I'll provide detailed information from our knowledge base."""
        else:
            # Multiple documents - show list
            doc_summary = ", ".join(doc_names)
            if len(kb_docs) > 5:
                doc_summary += f" and {len(kb_docs) - 5} more documents"
            
            message = f"""🤖 Hello! I'm here to help you with questions about our products/services.

📚 I have access to information about: {doc_summary}

💬 Please ask me any question about:
• Product specifications
• Features and benefits  
• Usage instructions
• Troubleshooting
• Pricing and availability

What would you like to know?

Reply to this message with your question and I'll provide detailed information from our knowledge base."""

        # Format phone number
        formatted_phone = phone_number
        if not formatted_phone.startswith('+'):
            formatted_phone = f"+1{formatted_phone.lstrip('+1')}"
        
        # Send WhatsApp message using Nexmo
        await nexmo_whatsapp_service.send_whatsapp_message(formatted_phone, message)
        
        whatsapp_event = CallEvent(
            event_type="whatsapp_knowledge_inquiry_sent",
            description=f"WhatsApp knowledge inquiry sent to {phone_number} for knowledge base {knowledge_base_id}"
        )
        
        # Update call metadata, preserving existing important fields
        current_metadata = fresh_call_doc.get("metadata", {})
        updated_metadata = {
            **current_metadata,  # Preserve all existing metadata including knowledge_base_only and call_type
            "whatsapp_knowledge_inquiry_sent": True,
            "whatsapp_knowledge_inquiry_time": datetime.utcnow().isoformat(),
            "knowledge_base_id": knowledge_base_id,
            "available_documents": len(kb_docs)
        }
        
        await calls_collection.update_one(
            {"_id": ObjectId(call_id)},
            {
                "$push": {"events": whatsapp_event.dict()},
                "$set": {
                    "updated_at": datetime.utcnow(),
                    "metadata": updated_metadata
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error sending WhatsApp knowledge inquiry for call {call_id}: {e}")
        raise
    
    logger.info(f"WhatsApp knowledge inquiry sent for call {call_id}", 
                extra={"user_id": user_id, "call_id": call_id, "knowledge_base_id": knowledge_base_id})

@router.post("/knowledge-inquiry", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_inquiry(
    phone_number: str = Body(..., description="Phone number to send inquiry to"),
    knowledge_base_id: str = Body(..., description="Knowledge base ID to use"),
    product_context: Optional[str] = Body(None, description="Specific product or topic context"),
    send_immediately: bool = Body(True, description="Send WhatsApp message immediately"),
    current_user: ClerkUser = Depends(get_current_user)
):
    """Create a knowledge base inquiry call (no survey needed)"""
    
    # Verify knowledge base exists and user has access
    knowledge_collection = MongoDB.get_collection("documents")
    kb_docs = await knowledge_collection.find({
        "owner_id": current_user.id,
        "status": "processed"
    }).to_list(length=1)
    
    if not kb_docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No processed knowledge base documents found. Please upload and process documents first."
        )
    
    # Create call data for knowledge inquiry
    call_data = CallCreate(
        phone_number=phone_number,
        survey_id="",  # Not needed for knowledge base only
        scheduled_time=datetime.utcnow(),
        notes=f"Knowledge base inquiry for: {product_context or 'General questions'}",
        priority=CallPriority.NORMAL,
        metadata={
            "knowledge_base_id": knowledge_base_id,
            "knowledge_base_only": True,
            "call_type": "knowledge_base_inquiry",
            "product_context": product_context
        }
    )
    
    # Create initial event
    event_description = f"Knowledge base inquiry scheduled for {phone_number}"
    if product_context:
        event_description += f" (Context: {product_context})"
    
    initial_event = CallEvent(
        event_type="knowledge_inquiry_scheduled",
        description=event_description
    )
    
    # Create call object
    call_db = CallDB(
        **call_data.dict(),
        owner_id=current_user.id,
        events=[initial_event]
    )
    
    # Insert into database
    calls_collection = MongoDB.get_collection("calls")
    result = await calls_collection.insert_one(call_db.dict(by_alias=True))
    
    # Get created call
    created_call = await calls_collection.find_one({"_id": result.inserted_id})
    call_id = str(result.inserted_id)
    
    # Send WhatsApp knowledge inquiry if requested
    if send_immediately:
        try:
            # Clear any pending surveys before sending knowledge base inquiry
            await clear_pending_surveys_for_phone(phone_number, "Knowledge Base inquiry call initiated")
            
            await send_whatsapp_knowledge_inquiry(call_id, current_user.id, knowledge_base_id, created_call)
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp knowledge inquiry for call {call_id}: {e}")
            # Don't fail the call creation, just log the error
            # Update with error info
            await calls_collection.update_one(
                {"_id": result.inserted_id},
                {
                    "$push": {"events": CallEvent(
                        event_type="whatsapp_send_failed",
                        description=f"Failed to send WhatsApp message: {str(e)}"
                    ).dict()},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
    
    logger.info(f"Knowledge base inquiry scheduled with ID: {result.inserted_id}", 
                extra={
                    "user_id": current_user.id, 
                    "phone_number": phone_number,
                    "knowledge_base_id": knowledge_base_id,
                    "product_context": product_context
                })
    
    return convert_call_doc(created_call)

async def clear_pending_surveys_for_phone(phone_number: str, reason: str):
    """
    Clear any pending surveys for a phone number to avoid conflicts with Knowledge Base Only calls
    """
    try:
        # Normalize phone number for matching
        normalized_number = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        
        # Find active (incomplete) survey results for this phone number
        results_collection = MongoDB.get_collection("survey_results")
        active_surveys = await results_collection.find({
            "contact_phone_number": {"$regex": normalized_number},
            "completed": False
        }).to_list(length=None)
        
        if not active_surveys:
            logger.info(f"📞 No pending surveys found for {phone_number}")
            return
        
        # Mark all active surveys as completed with a system reason
        completed_count = 0
        for survey_result in active_surveys:
            survey_result_id = str(survey_result["_id"])
            
            # Mark as completed with system metadata
            await results_collection.update_one(
                {"_id": survey_result["_id"]},
                {
                    "$set": {
                        "completed": True,
                        "end_time": datetime.utcnow(),
                        "completion_reason": "auto_cleared",
                        "completion_note": reason,
                        "auto_completed": True,
                        "overall_sentiment": None  # No sentiment analysis for auto-completed surveys
                    }
                }
            )
            
            # Update related call if exists
            if survey_result.get("call_id"):
                calls_collection = MongoDB.get_collection("calls")
                await calls_collection.update_one(
                    {"_id": ObjectId(survey_result["call_id"])},
                    {
                        "$set": {
                            "status": "auto_completed",
                            "updated_at": datetime.utcnow(),
                            "metadata.survey_auto_completed": True,
                            "metadata.auto_completion_reason": reason
                        }
                    }
                )
            
            completed_count += 1
            logger.info(f"🔄 Auto-completed pending survey {survey_result_id} for {phone_number}")
        
        logger.info(f"✅ Cleared {completed_count} pending surveys for {phone_number}. Reason: {reason}")
        
    except Exception as e:
        logger.error(f"❌ Error clearing pending surveys for {phone_number}: {e}")
        # Don't fail the main process if survey clearing fails