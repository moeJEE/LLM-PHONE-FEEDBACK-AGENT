import pymongo
from datetime import datetime

try:
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['llm_phone_feedback']
    
    # Get recent calls
    calls = list(db.calls.find().sort('_id', -1).limit(5))
    
    print("Recent calls:")
    for call in calls:
        phone = call.get('phone_number', 'N/A')
        call_type = call.get('call_type', 'N/A')
        created = call.get('created_at', 'N/A')
        print(f"- Phone: {phone} | Type: {call_type} | Created: {created}")
        
except Exception as e:
    print(f"Error: {e}") 