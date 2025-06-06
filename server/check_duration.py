#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the parent directory to the Python path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import get_db_connection
from app.api.calls import get_call_stats
from bson import ObjectId

async def check_duration():
    print('🔍 Checking call duration data...')
    
    # Get database connection
    db = await get_db_connection()
    if not db:
        print('❌ Failed to connect to database')
        return
    
    try:
        # Check available user IDs
        print('\n📋 Available user IDs in calls collection:')
        calls_cursor = db.calls.find({}, {'owner_id': 1})
        user_ids = set()
        async for call in calls_cursor:
            user_ids.add(call.get('owner_id'))
        
        print(f'Found user IDs: {list(user_ids)}')
        
        # Check available user IDs in survey results
        print('\n📋 Available user IDs linked to survey results:')
        pipeline = [
            {
                '$lookup': {
                    'from': 'calls',
                    'localField': 'call_id',
                    'foreignField': '_id',
                    'as': 'call_info'
                }
            },
            {
                '$match': {
                    'duration_seconds': {'$exists': True, '$ne': None, '$gt': 0},
                    'call_info': {'$ne': []}
                }
            },
            {
                '$unwind': '$call_info'
            },
            {
                '$group': {
                    '_id': '$call_info.owner_id',
                    'total_duration': {'$sum': '$duration_seconds'},
                    'avg_duration': {'$avg': '$duration_seconds'},
                    'count': {'$sum': 1}
                }
            }
        ]
        
        survey_users = []
        async for result in db.survey_results.aggregate(pipeline):
            user_id = result['_id']
            survey_users.append(user_id)
            print(f'  User: {user_id}')
            print(f'    Total duration: {result["total_duration"]} seconds')
            print(f'    Average duration: {result["avg_duration"]:.2f} seconds')
            print(f'    Number of calls: {result["count"]}')
        
        # Test the API with different users
        print('\n🧪 Testing API with different users:')
        
        # Test with users that have survey data
        for user_id in survey_users:
            print(f'\n📞 Testing user: {user_id}')
            try:
                result = await get_call_stats(user_id, db)
                print(f'  API result: {result}')
                avg_duration = result.get('average_duration_seconds', 0)
                if avg_duration > 0:
                    minutes = int(avg_duration // 60)
                    seconds = int(avg_duration % 60)
                    print(f'  ✅ Duration: {avg_duration:.2f}s = {minutes}:{seconds:02d}')
                else:
                    print(f'  ❌ No duration data returned')
            except Exception as e:
                print(f'  ❌ Error: {e}')
        
        # Test with the original user ID from the frontend
        original_user = 'user_2nOwl0jT7uKWUaEJPwxIV0f7uQY'  # This seems to be the default user
        print(f'\n📞 Testing original user: {original_user}')
        try:
            result = await get_call_stats(original_user, db)
            print(f'  API result: {result}')
            avg_duration = result.get('average_duration_seconds', 0)
            if avg_duration > 0:
                minutes = int(avg_duration // 60)
                seconds = int(avg_duration % 60)
                print(f'  ✅ Duration: {avg_duration:.2f}s = {minutes}:{seconds:02d}')
            else:
                print(f'  ❌ No duration data for this user')
                print('  💡 This explains why the frontend is showing 0:00')
        except Exception as e:
            print(f'  ❌ Error: {e}')
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
    
    finally:
        db.client.close()

if __name__ == "__main__":
    asyncio.run(check_duration()) 