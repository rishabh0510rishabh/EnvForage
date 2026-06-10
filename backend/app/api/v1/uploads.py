
# --- Comprehensive File Upload Pipeline ---
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Header
from typing import Optional
import aiofiles
import os
import magic
import logging

router = APIRouter()
logger = logging.getLogger("UploadPipeline")

UPLOAD_DIR = "/tmp/envforge_uploads"
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
):
    """
    Handles highly robust chunked and resumable file uploads.
    Validates MIME type via python-magic on the first chunk.
    """
    temp_file_path = os.path.join(UPLOAD_DIR, f"{x_upload_id}.part")
    
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
            final_path = os.path.join(UPLOAD_DIR, file.filename)
            os.rename(temp_file_path, final_path)
            
            # Simulate pushing to S3/Blob storage
            # await s3_client.upload_file(final_path, bucket, file.filename)
            
            logger.info(f"File upload complete: {file.filename}")
            return {"status": "complete", "filename": file.filename, "url": f"/media/{file.filename}"}
            
        return {"status": "uploading", "chunk": x_chunk_number}
        
    except Exception as e:
        logger.error(f"Upload failed for {x_upload_id} chunk {x_chunk_number}: {e}")
        raise HTTPException(status_code=500, detail="Chunk upload failed")
