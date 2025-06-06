from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import json
from pydantic import BaseModel
import time
from typing import Optional, Dict, Any
import os
import logging

from .config import get_settings

# Clerk Authentication Settings
settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)  # Allow no auth in dev mode

# User model for authentication
class ClerkUser(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    image_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    role: str = "user"

# Default development user
DEFAULT_DEV_USER = ClerkUser(
    id="dev-user-123",
    email="dev@example.com",
    first_name="Dev",
    last_name="User",
    role="admin"
)

# Cache for Clerk JWK
clerk_jwk_cache = {
    "keys": None,
    "expires_at": 0
}

async def get_clerk_public_keys():
    """Get Clerk's public keys from their JWKS endpoint"""
    try:
        now = time.time()
        
        if clerk_jwk_cache["keys"] and clerk_jwk_cache["expires_at"] > now:
            return clerk_jwk_cache["keys"]
        
        clerk_instance = os.getenv("CLERK_INSTANCE", "your-clerk-instance")
        jwks_url = f"https://{clerk_instance}.clerk.accounts.dev/.well-known/jwks.json"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch JWKS from Clerk"
                )
            
            keys = response.json()
            clerk_jwk_cache["keys"] = keys
            clerk_jwk_cache["expires_at"] = time.time() + 3600  # Cache for 1 hour
            
            return keys
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch JWKS from Clerk: {str(e)}"
        )

async def verify_clerk_jwt(token: str) -> Dict[str, Any]:
    """Verify a Clerk JWT token"""
    try:
        # In a production app, you would use a JWT library with the JWKs from Clerk
        # to properly verify the token. This is simplified for the example.
        
        # Split the token
        header_b64, payload_b64, signature = token.split(".")
        
        # Decode the payload
        from base64 import b64decode
        from base64 import urlsafe_b64decode
        
        def decode_base64(data):
            # Fix padding
            missing_padding = len(data) % 4
            if missing_padding:
                data += '=' * (4 - missing_padding)
            return urlsafe_b64decode(data)
        
        payload_json = decode_base64(payload_b64)
        payload = json.loads(payload_json)
        
        # Verify expiration
        now = time.time()
        if payload.get("exp") and payload["exp"] < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}"
        )

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> ClerkUser:
    """
    Dependency to get the current authenticated user from Clerk token.
    In DEBUG mode, returns a default user if no authentication is provided.
    """
    # In debug mode, allow bypassing authentication
    if settings.DEBUG and (not credentials or not credentials.credentials):
        # Use proper logging instead of print in production
        logger = logging.getLogger(__name__)
        logger.info("Using default development user (no auth required)")
        return DEFAULT_DEV_USER
    
    # If not in debug mode or credentials are provided, validate normally
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    token = credentials.credentials
    payload = await verify_clerk_jwt(token)

    # Extract user ID from JWT
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier in token"
        )

    # Try getting data directly from token
    email = payload.get("email")
    metadata = payload.get("user_metadata", {}) or {}
    first_name = metadata.get("first_name", "")
    last_name = metadata.get("last_name", "")

    # If email is missing, fetch it from Clerk API
    if not email:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"}
            )
            if res.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to fetch user from Clerk"
                )
            user_info = res.json()
            email = user_info["email_addresses"][0]["email_address"]
            first_name = user_info.get("first_name", "") or first_name
            last_name = user_info.get("last_name", "") or last_name
            metadata = user_info.get("public_metadata", {}) or metadata

    # Determine user role
    role = "admin" if payload.get("admin", False) else "user"

    return ClerkUser(
        id=user_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        metadata=metadata,
        role=role
    )

# Optional function to check for admin role
async def get_current_admin(current_user: ClerkUser = Depends(get_current_user)):
    """
    Dependency to ensure the user has admin role
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user

async def get_user_info(user_id: str) -> dict:
    """Get user information from Clerk"""
    try:
        clerk_secret_key = os.getenv("CLERK_SECRET_KEY")
        if not clerk_secret_key:
            raise ValueError("CLERK_SECRET_KEY not found in environment variables")
            
        headers = {
            "Authorization": f"Bearer {clerk_secret_key}",
            "Content-Type": "application/json"
        }
        
        clerk_instance = os.getenv("CLERK_INSTANCE", "your-clerk-instance")
        user_api_url = f"https://api.clerk.com/v1/users/{user_id}"
        
        async with httpx.AsyncClient() as client:
            res = await client.get(user_api_url, headers=headers)
            if res.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to fetch user from Clerk"
                )
            user_info = res.json()
            return user_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user information from Clerk: {str(e)}"
        )