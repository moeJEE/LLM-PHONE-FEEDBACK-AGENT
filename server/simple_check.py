import asyncio
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import get_db_connection
from app.api.calls import get_call_stats

async def check_duration():
    print('Checking call duration data...')
    
    db = await get_db_connection()
    if not db:
        print('Failed to connect to database')
        return
    
    try:
        # Check available user IDs
        print('\nAvailable user IDs in calls collection:')
        calls_cursor = db.calls.find({}, {'owner_id': 1})
        user_ids = set()
        async for call in calls_cursor:
            user_ids.add(call.get('owner_id'))
        
        print(f'Found user IDs: {list(user_ids)}')
        
        # Test with the original user ID from the frontend logs
        original_user = 'user_2nOwl0jT7uKWUaEJPwxIV0f7uQY'
        print(f'\nTesting original user: {original_user}')
        try:
            result = await get_call_stats(original_user, db)
            print(f'  API result: {result}')
            avg_duration = result.get('average_duration_seconds', 0)
            if avg_duration > 0:
                minutes = int(avg_duration // 60)
                seconds = int(avg_duration % 60)
                print(f'  Duration: {avg_duration:.2f}s = {minutes}:{seconds:02d}')
            else:
                print(f'  No duration data for this user')
                print('  This explains why the frontend is showing 0:00')
        except Exception as e:
            print(f'  Error: {e}')
        
        # Test with the user that has working data
        test_user = 'user_2vXoStlnWLx6VRj6noxwTrknlDy'
        print(f'\nTesting user with data: {test_user}')
        try:
            result = await get_call_stats(test_user, db)
            print(f'  API result: {result}')
            avg_duration = result.get('average_duration_seconds', 0)
            if avg_duration > 0:
                minutes = int(avg_duration // 60)
                seconds = int(avg_duration % 60)
                print(f'  Duration: {avg_duration:.2f}s = {minutes}:{seconds:02d}')
        except Exception as e:
            print(f'  Error: {e}')
        
    except Exception as e:
        print(f'Error: {e}')
    
    finally:
        db.client.close()

if __name__ == "__main__":
    asyncio.run(check_duration()) 