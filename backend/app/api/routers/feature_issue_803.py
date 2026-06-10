from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import JSONResponse
import time

router = APIRouter(prefix="/media", tags=["Media"])

# 5MB in bytes
MAX_PAYLOAD_SIZE = 5 * 1024 * 1024

# Simple in-memory rate limiter for demonstration
RATE_LIMIT_DURATION = 60 # seconds
RATE_LIMIT_REQUESTS = 5 # max requests per duration
rate_limit_records = {}

async def verify_content_length(request: Request):
    if "content-length" not in request.headers:
        raise HTTPException(status_code=411, detail="Length Required")
    content_length = int(request.headers.get("content-length"))
    if content_length > MAX_PAYLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Payload Too Large. Maximum allowed size is 5MB.")
    return content_length

async def rate_limiter(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    
    if client_ip not in rate_limit_records:
        rate_limit_records[client_ip] = []
        
    # Clean up old records
    rate_limit_records[client_ip] = [t for t in rate_limit_records[client_ip] if current_time - t < RATE_LIMIT_DURATION]
    
    if len(rate_limit_records[client_ip]) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(status_code=429, detail="Too Many Requests. Please try again later.")
        
    rate_limit_records[client_ip].append(current_time)
    return True

@router.post(
    "/upload",
    dependencies=[Depends(verify_content_length), Depends(rate_limiter)],
    summary="Upload Media (Issue #803)",
    description="Secure media upload endpoint with strict payload size limitations (5MB) and rate limiting to prevent DoS attacks."
)
async def upload_media(request: Request):
    """
    Handles media uploads securely.
    """
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("image/") and not content_type.startswith("video/"):
        raise HTTPException(status_code=415, detail="Unsupported Media Type. Only images and videos are allowed.")
        
    return JSONResponse(
        content={
            "message": "Media uploaded successfully",
            "size": request.headers.get("content-length"),
            "content_type": content_type
        },
        status_code=status.HTTP_201_CREATED
    )
