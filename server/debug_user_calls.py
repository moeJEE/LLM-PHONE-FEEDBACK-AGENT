import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, '.')

async def debug_user_calls():
    print('Debugging user calls and survey results...')
    
    # Import inside the function to avoid module issues
    from app.config.database import get_db_connection
    from bson import ObjectId
    
    db = await get_db_connection()
    if not db:
        print('Failed to connect to database')
        return
    
    try:
        user_id = 'user_2nOwl0jT7uKWUaEJPwxIV0f7uQY'
        print(f'\nChecking data for user: {user_id}')
        
        # 1. Check calls for this user
        print('\n=== CALLS ===')
        calls_cursor = db.calls.find({'owner_id': user_id})
        calls = await calls_cursor.to_list(length=None)
        print(f'Found {len(calls)} calls for user {user_id}')
        
        call_ids = []
        for i, call in enumerate(calls):
            call_id = call['_id']
            call_ids.append(call_id)
            status = call.get('status', 'unknown')
            created = call.get('created_at', 'unknown')
            print(f'  Call {i+1}: {call_id} - Status: {status} - Created: {created}')
        
        # 2. Check survey results for these calls
        print('\n=== SURVEY RESULTS ===')
        if call_ids:
            # Check both string and ObjectId formats
            string_call_ids = [str(call_id) for call_id in call_ids]
            
            survey_cursor = db.survey_results.find({
                '$or': [
                    {'call_id': {'$in': call_ids}},  # ObjectId format
                    {'call_id': {'$in': string_call_ids}}  # string format
                ]
            })
            surveys = await survey_cursor.to_list(length=None)
            print(f'Found {len(surveys)} survey results for these calls')
            
            for i, survey in enumerate(surveys):
                call_id = survey.get('call_id')
                duration = survey.get('duration_seconds')
                completed = survey.get('completed', False)
                created = survey.get('created_at', 'unknown')
                print(f'  Survey {i+1}: Call {call_id} - Duration: {duration} - Completed: {completed} - Created: {created}')
                
                # Check if this survey has the required fields
                if duration is None:
                    print(f'    ❌ Missing duration_seconds field')
                elif duration <= 0:
                    print(f'    ❌ Duration is zero or negative: {duration}')
                else:
                    print(f'    ✅ Valid duration: {duration} seconds')
        else:
            print('No calls found, so no survey results to check')
        
        # 3. Test the aggregation pipeline directly
        print('\n=== AGGREGATION TEST ===')
        if call_ids:
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
                    "pipeline": [{"$match": {"owner_id": user_id}}]
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
            
            agg_result = await db.survey_results.aggregate(duration_pipeline).to_list(length=1)
            print(f'Aggregation result: {agg_result}')
            
            if agg_result:
                result = agg_result[0]
                print(f'✅ Average duration: {result.get("avg_duration", 0)} seconds')
                print(f'✅ Total duration: {result.get("total_duration", 0)} seconds')
                print(f'✅ Count: {result.get("count", 0)} calls')
            else:
                print('❌ No results from aggregation - this explains why duration is 0')
                
                # Let's debug the pipeline step by step
                print('\n=== DEBUGGING PIPELINE ===')
                
                # Step 1: Get all survey results with duration
                step1_cursor = db.survey_results.find({
                    "duration_seconds": {"$exists": True, "$ne": None, "$gt": 0}
                })
                step1_results = await step1_cursor.to_list(length=None)
                print(f'Step 1: {len(step1_results)} survey results with duration > 0')
                
                # Step 2: Test the lookup manually
                if step1_results:
                    sample_survey = step1_results[0]
                    sample_call_id = sample_survey.get('call_id')
                    print(f'Sample survey call_id: {sample_call_id} (type: {type(sample_call_id)})')
                    
                    # Try to find the call
                    if isinstance(sample_call_id, str):
                        try:
                            sample_call_obj_id = ObjectId(sample_call_id)
                            call_doc = await db.calls.find_one({'_id': sample_call_obj_id, 'owner_id': user_id})
                            print(f'Found call with ObjectId conversion: {call_doc is not None}')
                        except:
                            print('Failed to convert call_id to ObjectId')
                    else:
                        call_doc = await db.calls.find_one({'_id': sample_call_id, 'owner_id': user_id})
                        print(f'Found call without conversion: {call_doc is not None}')
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    
    finally:
        db.client.close()

if __name__ == "__main__":
    asyncio.run(debug_user_calls()) 