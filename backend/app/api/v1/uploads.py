
# --- Comprehensive File Upload Pipeline ---
import logging
import os

import aiofiles
import magic
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.middleware.rate_limit import general_rate_limit

router = APIRouter()
logger = logging.getLogger("UploadPipeline")

UPLOAD_DIR = "/tmp/envforage_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/csv",
    "application/json"
}

@router.post("/upload/chunked")
async def upload_chunked_file(
    file: UploadFile = File(...),
    x_upload_id: str = Header(...),
    x_chunk_number: int = Header(...),
    x_total_chunks: int = Header(...),
    _user: str = Depends(get_current_user),
    _rate_limit: None = Depends(general_rate_limit),
):
    """
    Handles highly robust chunked and resumable file uploads.
    Validates MIME type via python-magic on the first chunk.
    """
    # Sanitize upload ID to prevent path traversal in temp file name
    safe_upload_id = os.path.basename(x_upload_id)
    if not safe_upload_id or safe_upload_id != x_upload_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload ID",
        )
    temp_file_path = os.path.join(UPLOAD_DIR, f"{safe_upload_id}.part")

    try:
        chunk_data = await file.read()

        # Validate magic number on first chunk
        if x_chunk_number == 1:
            mime = magic.from_buffer(chunk_data, mime=True)
            if mime not in ALLOWED_MIME_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Unsupported file type: {mime}"
                )

        # Append chunk
        mode = "ab" if x_chunk_number > 1 else "wb"
        async with aiofiles.open(temp_file_path, mode) as f:
            await f.write(chunk_data)

        logger.debug(f"Received chunk {x_chunk_number}/{x_total_chunks} for {x_upload_id}")

        # If final chunk, assemble and move
        if x_chunk_number == x_total_chunks:
            raw_name = file.filename or "uploaded_file"
            # Security: strip all path components to prevent path traversal
            # (e.g. "../../etc/cron.d/pwned" → "pwned")
            filename = os.path.basename(raw_name)
            # Reject filenames with only unsafe characters
            if not filename or filename.startswith("."):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or unsafe filename",
                )
            final_path = os.path.join(UPLOAD_DIR, filename)
            os.rename(temp_file_path, final_path)

            # Simulate pushing to S3/Blob storage
            # await s3_client.upload_file(final_path, bucket, filename)

            logger.info(f"File upload complete: {filename}")
            return {"status": "complete", "filename": filename, "url": f"/media/{filename}"}

        return {"status": "uploading", "chunk": x_chunk_number}

    except Exception as e:
        logger.error(f"Upload failed for {x_upload_id} chunk {x_chunk_number}: {e}")
        raise HTTPException(status_code=500, detail="Chunk upload failed")
