#!/usr/bin/env python3

import asyncio
from datetime import datetime, timedelta
import random
from bson import ObjectId

async def create_test_duration_data():
    """Create survey results with duration data for the user's existing calls"""
    
    from .config.database import get_db_connection
    from .models.survey import SurveyResult
    
    db = await get_db_connection()
    if not db:
        print('❌ Failed to connect to database')
        return
    
    try:
        user_id = 'user_2nOwl0jT7uKWUaEJPwxIV0f7uQY'
        print(f'🔧 Creating test duration data for user: {user_id}')
        
        # Get user's calls
        calls_cursor = db.calls.find({'owner_id': user_id})
        calls = await calls_cursor.to_list(length=None)
        print(f'📞 Found {len(calls)} calls for user')
        
        if not calls:
            print('❌ No calls found for user. Please create some calls first.')
            return
        
        # Check if survey results already exist
        call_ids = [str(call['_id']) for call in calls]
        existing_surveys = await db.survey_results.find({
            'call_id': {'$in': call_ids}
        }).to_list(length=None)
        
        print(f'📋 Found {len(existing_surveys)} existing survey results')
        
        # Create survey results with duration for calls that don't have them
        created_count = 0
        for call in calls[:5]:  # Limit to first 5 calls
            call_id_str = str(call['_id'])
            
            # Check if survey result already exists
            existing = any(s['call_id'] == call_id_str for s in existing_surveys)
            if existing:
                print(f'📝 Survey result already exists for call {call_id_str}')
                continue
            
            # Generate random duration between 15-120 seconds
            duration = random.randint(15, 120)
            
            # Create survey result with duration
            survey_result = {
                'survey_id': '507f1f77bcf86cd799439015',  # Default survey ID
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
            
            # Insert survey result
            result = await db.survey_results.insert_one(survey_result)
            print(f'✅ Created survey result for call {call_id_str} with {duration}s duration')
            created_count += 1
        
        if created_count > 0:
            print(f'\n🎉 Created {created_count} survey results with duration data')
            
            # Test the API now
            from .api.calls import get_call_stats
            from .auth import ClerkUser
            
            # Create a mock user object
            class MockUser:
                def __init__(self, user_id):
                    self.id = user_id
            
            mock_user = MockUser(user_id)
            stats = await get_call_stats_internal(mock_user, db)
            
            print(f'\n📊 API Results:')
            print(f'   Average duration: {stats.get("average_duration_seconds", 0)} seconds')
            print(f'   Total duration: {stats.get("total_duration_seconds", 0)} seconds')
            
            if stats.get("average_duration_seconds", 0) > 0:
                avg = stats["average_duration_seconds"]
                minutes = int(avg // 60)
                seconds = int(avg % 60)
                print(f'   Formatted: {minutes}:{seconds:02d}')
            
        else:
            print('ℹ️ No new survey results created (all calls already have survey results)')
            
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
    
    finally:
        db.client.close()

async def get_call_stats_internal(current_user, db):
    """Internal function to get call stats"""
    from .database import MongoDB
    
    base_query = {"owner_id": current_user.id}
    calls_collection = db.calls
    survey_results_collection = db.survey_results
    
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

if __name__ == "__main__":
    asyncio.run(create_test_duration_data()) 