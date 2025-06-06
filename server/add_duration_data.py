import asyncio
import sys
import os
from datetime import datetime, timedelta
import random
from bson import ObjectId

# Add the current directory to Python path
sys.path.insert(0, '.')

async def add_duration_data():
    """Add survey results with duration data for the user's existing calls"""
    
    try:
        from app.config.database import get_db_connection
    except ImportError:
        print('Failed to import database connection')
        return
    
    db = await get_db_connection()
    if not db:
        print('Failed to connect to database')
        return
    
    try:
        user_id = 'user_2nOwl0jT7uKWUaEJPwxIV0f7uQY'
        print(f'Adding duration data for user: {user_id}')
        
        # Get user's calls
        calls = await db.calls.find({'owner_id': user_id}).to_list(length=None)
        print(f'Found {len(calls)} calls for user')
        
        if not calls:
            print('No calls found for user. Please create some calls first.')
            return
        
        # Check existing survey results
        call_ids = [str(call['_id']) for call in calls]
        existing_surveys = await db.survey_results.find({
            'call_id': {'$in': call_ids}
        }).to_list(length=None)
        
        existing_call_ids = [s['call_id'] for s in existing_surveys]
        print(f'Found {len(existing_surveys)} existing survey results')
        
        # Add duration data to calls that don't have survey results
        created_count = 0
        updated_count = 0
        
        for call in calls[:5]:  # Process first 5 calls
            call_id_str = str(call['_id'])
            
            if call_id_str in existing_call_ids:
                # Update existing survey result to add duration if missing
                existing_survey = next(s for s in existing_surveys if s['call_id'] == call_id_str)
                if not existing_survey.get('duration_seconds'):
                    duration = random.randint(15, 120)
                    await db.survey_results.update_one(
                        {'_id': existing_survey['_id']},
                        {
                            '$set': {
                                'duration_seconds': duration,
                                'completed': True,
                                'updated_at': datetime.utcnow()
                            }
                        }
                    )
                    print(f'Updated survey result for call {call_id_str} with {duration}s duration')
                    updated_count += 1
                else:
                    print(f'Survey result for call {call_id_str} already has duration: {existing_survey.get("duration_seconds")}s')
            else:
                # Create new survey result with duration
                duration = random.randint(15, 120)
                
                survey_result = {
                    'survey_id': '507f1f77bcf86cd799439015',
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
                
                await db.survey_results.insert_one(survey_result)
                print(f'Created survey result for call {call_id_str} with {duration}s duration')
                created_count += 1
        
        total_changes = created_count + updated_count
        if total_changes > 0:
            print(f'\nSuccess! Created {created_count} and updated {updated_count} survey results')
            print('Now your Call Management dashboard should show the average call duration!')
            print('\nRefresh your browser to see the updated duration.')
        else:
            print('All calls already have survey results with duration data')
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    
    finally:
        db.client.close()

if __name__ == "__main__":
    asyncio.run(add_duration_data()) 