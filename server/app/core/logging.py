import logging
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from .config import get_settings

settings = get_settings()

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Configure logging
class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the log record.
    """
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "module",
                "msecs", "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread", "threadName"
            }:
                log_record[key] = value
                
        return json.dumps(log_record)

def setup_logger(name: str, level=None):
    """
    Set up a logger with the specified name and level.
    """
    if level is None:
        level = logging.DEBUG if settings.DEBUG else logging.INFO
        
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (JSON)
    file_handler = logging.FileHandler(log_dir / f"{name.replace('.', '_')}.log")
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)
    
    return logger

# Create loggers
app_logger = setup_logger("app")
api_logger = setup_logger("api")
db_logger = setup_logger("db")

# Request logging middleware
async def log_request(request, call_next):
    """
    Middleware to log request and response details.
    """
    request_id = request.headers.get("x-request-id", "unknown")
    
    request_details = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host,
        "user_agent": request.headers.get("user-agent", "unknown")
    }
    
    api_logger.info(f"Request received: {request.method} {request.url.path}", extra=request_details)
    
    try:
        response = await call_next(request)
        
        response_details = {
            **request_details,
            "status_code": response.status_code
        }
        
        api_logger.info(f"Response sent: {response.status_code}", extra=response_details)
        
        return response
    except Exception as e:
        error_details = {
            **request_details,
            "error": str(e),
            "exception_type": type(e).__name__
        }
        
        api_logger.error(f"Error processing request: {str(e)}", exc_info=True, extra=error_details)
        raise

def log_function_call(func_name: str, params: Dict[str, Any] = None, result: Any = None, error: Exception = None):
    """
    Log a function call with parameters and result.
    """
    log_data = {
        "function": func_name,
        "params": params or {}
    }
    
    if error:
        app_logger.error(f"Error in {func_name}: {str(error)}", exc_info=True, extra=log_data)
    else:
        # Don't log the actual result as it might be large or contain sensitive data
        app_logger.debug(f"Function {func_name} called", extra=log_data)
        
def get_logger(name: str):
    """
    Get a configured logger for the specified module.
    """
    return setup_logger(f"app.{name}")