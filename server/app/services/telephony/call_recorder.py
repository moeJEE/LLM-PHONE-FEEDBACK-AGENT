from typing import Dict, Any, Optional, Union, BinaryIO
import os
import io
import aiohttp
import asyncio
from datetime import datetime
from pathlib import Path

from ...core.config import get_settings
from ...core.logging import get_logger

logger = get_logger("services.telephony.call_recorder")
settings = get_settings()

class CallRecorder:
    """
    Service for managing call recordings, including downloading, storing, and retrieving them.
    """
    
    def __init__(self):
        """Initialize call recorder service"""
        # Set up recordings directory
        self.recordings_dir = Path("recordings")
        self.recordings_dir.mkdir(exist_ok=True)
    
    async def download_recording(
        self, 
        recording_url: str,
        call_sid: str,
        file_format: str = "mp3"
    ) -> Dict[str, Any]:
        """
        Download a recording from a URL (typically from Twilio)
        
        Args:
            recording_url: URL of the recording
            call_sid: Call SID associated with the recording
            file_format: Audio format of the recording
            
        Returns:
            Dict: Download result with local file path
        """
        try:
            # Create a sanitized filename
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            filename = f"{call_sid}_{timestamp}.{file_format}"
            file_path = self.recordings_dir / filename
            
            # Download the file
            async with aiohttp.ClientSession() as session:
                async with session.get(recording_url) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"Failed to download recording: HTTP {response.status}",
                            "call_sid": call_sid
                        }
                    
                    # Read response and write to file
                    data = await response.read()
                    with open(file_path, "wb") as f:
                        f.write(data)
            
            return {
                "success": True,
                "file_path": str(file_path),
                "call_sid": call_sid,
                "size_bytes": file_path.stat().st_size,
                "format": file_format,
                "timestamp": timestamp
            }
        
        except Exception as e:
            logger.error(f"Error downloading recording for call {call_sid}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "call_sid": call_sid
            }
    
    async def get_recording_path(self, call_sid: str) -> Optional[Path]:
        """
        Get the path to a recording file for a specific call
        
        Args:
            call_sid: Call SID to look for
            
        Returns:
            Optional[Path]: Path to the recording file if found, None otherwise
        """
        try:
            # Find files matching the pattern
            matching_files = list(self.recordings_dir.glob(f"{call_sid}_*.mp3"))
            
            # Return the most recent one if multiple exist
            if matching_files:
                return sorted(matching_files)[-1]
            
            return None
        
        except Exception as e:
            logger.error(f"Error finding recording for call {call_sid}: {str(e)}", exc_info=True)
            return None
    
    async def delete_recording(self, call_sid: str) -> bool:
        """
        Delete a recording file for a specific call
        
        Args:
            call_sid: Call SID to delete recording for
            
        Returns:
            bool: Whether the deletion was successful
        """
        try:
            recording_path = await self.get_recording_path(call_sid)
            
            if not recording_path:
                logger.warning(f"No recording found for call {call_sid}")
                return False
            
            # Delete the file
            recording_path.unlink()
            logger.info(f"Deleted recording for call {call_sid}: {recording_path}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting recording for call {call_sid}: {str(e)}", exc_info=True)
            return False
    
    async def list_recordings(
        self, 
        limit: int = 100, 
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List available recordings
        
        Args:
            limit: Maximum number of recordings to return
            offset: Offset for pagination
            
        Returns:
            Dict: List of recordings with metadata
        """
        try:
            # Get all recording files
            all_recordings = list(self.recordings_dir.glob("*.mp3"))
            all_recordings.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Apply pagination
            paginated = all_recordings[offset:offset+limit]
            
            # Extract metadata
            recordings = []
            for path in paginated:
                try:
                    # Extract call SID and timestamp from filename
                    filename = path.name
                    parts = filename.split('_')
                    
                    if len(parts) >= 2:
                        call_sid = parts[0]
                        timestamp_with_ext = parts[1]
                        timestamp = os.path.splitext(timestamp_with_ext)[0]
                        
                        recordings.append({
                            "call_sid": call_sid,
                            "file_path": str(path),
                            "filename": filename,
                            "timestamp": timestamp,
                            "size_bytes": path.stat().st_size,
                            "created_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat()
                        })
                except Exception as e:
                    logger.warning(f"Error extracting metadata for recording {path}: {str(e)}")
            
            return {
                "success": True,
                "recordings": recordings,
                "total": len(all_recordings),
                "limit": limit,
                "offset": offset
            }
        
        except Exception as e:
            logger.error(f"Error listing recordings: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "recordings": []
            }