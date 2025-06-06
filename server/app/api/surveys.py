from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict
from datetime import datetime
from bson import ObjectId

from ..core.security import get_current_user, ClerkUser
from ..core.logging import get_logger
from ..core.config import get_settings
from ..db.mongodb import MongoDB
from ..models.survey import (
    SurveyCreate, 
    SurveyUpdate, 
    SurveyResponse, 
    SurveyDB,
    SurveyStatus,
    SurveyResult
)

logger = get_logger("api.surveys")
router = APIRouter()
settings = get_settings()

# Helper function to convert MongoDB document to Pydantic model
def convert_survey_doc(survey_doc):
    if not survey_doc:
        return None
    
    survey_doc["id"] = str(survey_doc.pop("_id"))
    return SurveyResponse(**survey_doc)

# Endpoints
@router.post("/", response_model=SurveyResponse, status_code=status.HTTP_201_CREATED)
async def create_survey(
    survey: SurveyCreate, 
    current_user: ClerkUser = Depends(get_current_user)
):
    """Create a new survey"""
    # Create survey object with user info
    survey_db = SurveyDB(
        **survey.dict(),
        owner_id=current_user.id
    )
    
    # Insert into database
    surveys_collection = MongoDB.get_collection("surveys")
    result = await surveys_collection.insert_one(survey_db.dict(by_alias=True))
    
    # Get created survey
    created_survey = await surveys_collection.find_one({"_id": result.inserted_id})
    
    logger.info(f"Survey created with ID: {result.inserted_id}", extra={"user_id": current_user.id})
    
    return convert_survey_doc(created_survey)

@router.get("/", response_model=List[SurveyResponse])
async def get_surveys(
    current_user: ClerkUser = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by survey status"),
    skip: int = Query(0, ge=0, description="Number of surveys to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of surveys to return")
):
    """Get surveys for the authenticated user"""
    surveys_collection = MongoDB.get_collection("surveys")
    
    # Build query - filter by current user's ID
    query = {"owner_id": current_user.id}
    if status:
        if status not in [s.value for s in SurveyStatus]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
        query["status"] = status
    
    # Execute query
    cursor = surveys_collection.find(query).skip(skip).limit(limit)
    surveys = await cursor.to_list(length=limit)
    
    logger.info(f"Retrieved {len(surveys)} surveys for user {current_user.id}")
    
    return [convert_survey_doc(survey) for survey in surveys]

@router.get("/{survey_id}", response_model=SurveyResponse)
async def get_survey(
    survey_id: str,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Get a specific survey by ID"""
    surveys_collection = MongoDB.get_collection("surveys")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(survey_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid survey ID format"
        )
    
    # Find survey
    survey = await surveys_collection.find_one({
        "_id": ObjectId(survey_id),
        "owner_id": current_user.id
    })
    
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    return convert_survey_doc(survey)

@router.put("/{survey_id}", response_model=SurveyResponse)
async def update_survey(
    survey_id: str,
    survey_update: SurveyUpdate,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Update a survey"""
    surveys_collection = MongoDB.get_collection("surveys")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(survey_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid survey ID format"
        )
    
    # Find survey
    existing_survey = await surveys_collection.find_one({
        "_id": ObjectId(survey_id),
        "owner_id": current_user.id
    })
    
    if not existing_survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Remove None values from update
    update_data = {k: v for k, v in survey_update.dict().items() if v is not None}
    
    # Always update the updated_at timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    # Update survey
    await surveys_collection.update_one(
        {"_id": ObjectId(survey_id)},
        {"$set": update_data}
    )
    
    # Get updated survey
    updated_survey = await surveys_collection.find_one({"_id": ObjectId(survey_id)})
    
    logger.info(f"Survey updated with ID: {survey_id}", extra={"user_id": current_user.id})
    
    return convert_survey_doc(updated_survey)

@router.delete("/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_survey(
    survey_id: str,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Delete a survey"""
    surveys_collection = MongoDB.get_collection("surveys")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(survey_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid survey ID format"
        )
    
    # Check if survey exists and belongs to user
    existing_survey = await surveys_collection.find_one({
        "_id": ObjectId(survey_id),
        "owner_id": current_user.id
    })
    
    if not existing_survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Delete survey
    await surveys_collection.delete_one({"_id": ObjectId(survey_id)})
    
    logger.info(f"Survey deleted with ID: {survey_id}", extra={"user_id": current_user.id})

@router.post("/{survey_id}/activate", response_model=SurveyResponse)
async def activate_survey(
    survey_id: str,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Activate a survey"""
    surveys_collection = MongoDB.get_collection("surveys")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(survey_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid survey ID format"
        )
    
    # Find survey
    existing_survey = await surveys_collection.find_one({
        "_id": ObjectId(survey_id),
        "owner_id": current_user.id
    })
    
    if not existing_survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Update survey status
    await surveys_collection.update_one(
        {"_id": ObjectId(survey_id)},
        {"$set": {"status": SurveyStatus.ACTIVE.value, "updated_at": datetime.utcnow()}}
    )
    
    # Get updated survey
    updated_survey = await surveys_collection.find_one({"_id": ObjectId(survey_id)})
    
    logger.info(f"Survey activated with ID: {survey_id}", extra={"user_id": current_user.id})
    
    return convert_survey_doc(updated_survey)

@router.get("/{survey_id}/results", response_model=List[SurveyResult])
async def get_survey_results(
    survey_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: ClerkUser = Depends(get_current_user)
):
    """Get results for a specific survey"""
    surveys_collection = MongoDB.get_collection("surveys")
    results_collection = MongoDB.get_collection("survey_results")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(survey_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid survey ID format"
        )
    
    # Check if survey exists and belongs to user
    existing_survey = await surveys_collection.find_one({
        "_id": ObjectId(survey_id),
        "owner_id": current_user.id
    })
    
    if not existing_survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Get results
    cursor = results_collection.find({"survey_id": survey_id}).skip(skip).limit(limit)
    results = await cursor.to_list(length=limit)
    
    # Convert results
    return [
        SurveyResult(**{**result, "id": str(result["_id"])})
        for result in results
    ]

@router.get("/stats/summary")
async def get_survey_stats(
    current_user: ClerkUser = Depends(get_current_user)
):
    """Get survey statistics summary"""
    
    surveys_collection = MongoDB.get_collection("surveys")
    calls_collection = MongoDB.get_collection("calls")
    
    # Get surveys for the current user
    user_surveys = await surveys_collection.find({"owner_id": current_user.id}).to_list(length=None)
    
    # Calculate survey type distribution based on survey titles/descriptions
    survey_types = {
        "Customer Satisfaction": 0,
        "Product Feedback": 0,
        "Technical Support": 0,
        "Other": 0
    }
    
    total_surveys = len(user_surveys)
    
    for survey in user_surveys:
        title = survey.get("title", "").lower()
        description = survey.get("description", "").lower()
        
        # Categorize based on keywords in title and description
        if any(keyword in title or keyword in description for keyword in ["satisfaction", "rating", "experience", "service"]):
            survey_types["Customer Satisfaction"] += 1
        elif any(keyword in title or keyword in description for keyword in ["product", "feature", "improvement", "feedback"]):
            survey_types["Product Feedback"] += 1
        elif any(keyword in title or keyword in description for keyword in ["support", "technical", "help", "issue", "problem"]):
            survey_types["Technical Support"] += 1
        else:
            survey_types["Other"] += 1
    
    # Calculate percentages
    survey_type_percentages = {}
    if total_surveys > 0:
        for survey_type, count in survey_types.items():
            if survey_type != "Other" or count > 0:  # Only include "Other" if it has surveys
                survey_type_percentages[survey_type] = round((count / total_surveys) * 100, 1)
    else:
        # Default values if no surveys exist
        survey_type_percentages = {
            "Customer Satisfaction": 0.0,
            "Product Feedback": 0.0,
            "Technical Support": 0.0
        }
    
    logger.info(f"Retrieved survey stats for user {current_user.id}", 
                extra={"user_id": current_user.id, "total_surveys": total_surveys})
    
    return {
        "total_surveys": total_surveys,
        "survey_type_distribution": survey_type_percentages,
        "active_surveys": len([s for s in user_surveys if s.get("status") == "active"]),
        "draft_surveys": len([s for s in user_surveys if s.get("status") == "draft"])
    }