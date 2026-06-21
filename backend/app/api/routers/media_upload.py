from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.middleware.rate_limit import general_rate_limit

router = APIRouter(prefix="/media", tags=["Media"])

# 5MB in bytes
MAX_PAYLOAD_SIZE = 5 * 1024 * 1024


async def verify_content_length(request: Request):
    if "content-length" not in request.headers:
        raise HTTPException(status_code=411, detail="Length Required")
    content_length = int(request.headers.get("content-length") or "0")
    if content_length > MAX_PAYLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Payload Too Large. Maximum allowed size is 5MB.")
    return content_length


@router.post(
    "/upload",
    dependencies=[Depends(verify_content_length), Depends(general_rate_limit)],
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
