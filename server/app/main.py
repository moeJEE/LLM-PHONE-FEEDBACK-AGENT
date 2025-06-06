from fastapi import FastAPI, Depends, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import uvicorn
from contextlib import asynccontextmanager

from .core.config import get_settings
from .core.logging import log_request, app_logger
from .db.mongodb import MongoDB
from .api import auth, calls, knowledge, surveys, twilio_webhooks, nexmo_webhooks, test_whatsapp, optimization

settings = get_settings()

# Startup and shutdown handlers
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app_logger.info("Starting application...")
    
    # Connect to databases
    await MongoDB.connect()
    
    # Perform any additional startup tasks here
    app_logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    app_logger.info("Shutting down application...")
    
    # Close database connections
    await MongoDB.close()
    
    # Perform any additional cleanup tasks here
    app_logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="LLM Phone Feedback System API",
    description="API for LLM-enhanced phone feedback system",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    return await log_request(request, call_next)

# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    app_logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred, please try again later"}
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Check if the API is running and connectable"""
    return {"status": "healthy", "environment": settings.ENVIRONMENT}

# Include routers
app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(calls.router, prefix="/api/calls", tags=["Calls"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge Base"])
app.include_router(surveys.router, prefix="/api/surveys", tags=["Surveys"])
app.include_router(twilio_webhooks.router, prefix="/api/webhooks/twilio", tags=["Twilio Webhooks"])
app.include_router(nexmo_webhooks.router, prefix="/api/webhooks/nexmo", tags=["Nexmo Webhooks"])
app.include_router(test_whatsapp.router, prefix="/api", tags=["WhatsApp Testing"])
app.include_router(optimization.router, prefix="/api", tags=["Optimization"])

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "LLM Phone Feedback System API",
        "version": "0.1.0",
        "documentation": "/docs",
        "environment": settings.ENVIRONMENT
    }

# Emergency webhook routes
@app.post("/emergency/voice")
async def emergency_voice():
    """Emergency voice webhook - simple and fast"""
    twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Hello! Thank you for calling our survey. Press 1 to start or say something.</Say>
    <Gather input="dtmf speech" action="https://c6ef-197-153-72-10.ngrok-free.app/emergency/gather" method="POST">
        <Say>Please press 1 or say ready when you're ready to begin.</Say>
    </Gather>
    <Say>Thank you, goodbye.</Say>
</Response>'''
    return Response(content=twiml, media_type="application/xml")

@app.post("/emergency/gather")
async def emergency_gather(
    CallSid: str = Form(None),
    Digits: str = Form(None), 
    SpeechResult: str = Form(None)
):
    """Emergency gather webhook - simple and fast"""
    
    print(f"📞 Emergency Webhook Called on Main Server!")
    print(f"   CallSid: {CallSid}")
    print(f"   Digits: {Digits}")
    print(f"   Speech: {SpeechResult}")
    
    # Simple response based on input
    if Digits == "1" or (SpeechResult and "ready" in SpeechResult.lower()):
        # First question
        twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="dtmf speech" action="https://c6ef-197-153-72-10.ngrok-free.app/emergency/gather" method="POST" timeout="15" speechTimeout="auto">
        <Say>On a scale from 1 to 5, how satisfied are you with our service? You can press a number or say your rating.</Say>
    </Gather>
    <Say>Thank you for your feedback!</Say>
</Response>'''
    else:
        # Thank you message for any other response
        twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for your response! Your feedback has been recorded. Goodbye!</Say>
    <Hangup/>
</Response>'''
    
    return Response(content=twiml, media_type="application/xml")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", 
        host=settings.API_HOST, 
        port=settings.API_PORT,
        reload=settings.DEBUG
    )