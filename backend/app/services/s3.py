
# --- S3 Blob Storage Interface ---
import logging
from typing import Any

try:
    import aioboto3
    from botocore.exceptions import ClientError
    AIOBOTO3_AVAILABLE = True
except ImportError:
    AIOBOTO3_AVAILABLE = False
    # Placeholder so type annotations and except clauses don't break
    ClientError = Exception  # type: ignore[assignment,misc]

logger = logging.getLogger("S3Storage")

class S3StorageService:
    """
    An asynchronous wrapper around AWS S3 using aioboto3.
    Supports bucket creation, file uploading, and generating pre-signed URLs
    for direct client-to-S3 uploads, reducing backend bandwidth overhead.
    """
    def __init__(self, region_name: str, aws_access_key_id: str, aws_secret_access_key: str, bucket_name: str):
        self.region_name = region_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.bucket_name = bucket_name

        if AIOBOTO3_AVAILABLE:
            self.session = aioboto3.Session(
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name
            )

    async def upload_file(self, file_content: bytes, object_name: str, content_type: str = "application/octet-stream") -> bool:
        """Uploads bytes directly to the S3 bucket."""
        if not AIOBOTO3_AVAILABLE:
            logger.warning("aioboto3 not installed. Simulated S3 upload.")
            return True

        try:
            async with self.session.client("s3") as s3_client:
                await s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                    Body=file_content,
                    ContentType=content_type
                )
            logger.info(f"Successfully uploaded {object_name} to {self.bucket_name}")
            return True
        except ClientError as e:
            logger.error(f"S3 Upload failed: {e}")
            return False

    async def generate_presigned_url(self, object_name: str, expiration_seconds: int = 3600) -> str | None:
        """
        Generates a temporary URL allowing clients to download a private file.
        """
        if not AIOBOTO3_AVAILABLE:
            return f"https://mock-s3-url.com/{self.bucket_name}/{object_name}?sig=mock"

        try:
            async with self.session.client("s3") as s3_client:
                response = await s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': object_name},
                    ExpiresIn=expiration_seconds
                )
            return response
        except ClientError as e:
            logger.error(f"Failed to generate S3 presigned URL: {e}")
            return None

    async def generate_presigned_post(self, object_name: str, conditions: list[Any] | None = None, expiration_seconds: int = 3600) -> dict[str, Any] | None:
        """
        Generates a pre-signed POST payload allowing browsers to upload files
        directly to S3 without passing through the backend, bounded by conditions (e.g. file size limits).
        """
        if not AIOBOTO3_AVAILABLE:
            return {"url": "https://mock-s3", "fields": {"key": object_name}}

        try:
            async with self.session.client("s3") as s3_client:
                response = await s3_client.generate_presigned_post(
                    self.bucket_name,
                    object_name,
                    Conditions=conditions,
                    ExpiresIn=expiration_seconds
                )
            return response
        except ClientError as e:
            logger.error(f"Failed to generate S3 presigned POST: {e}")
            return None


def get_s3_service() -> S3StorageService | None:
    """Create an S3StorageService from app settings, or None if unconfigured."""
    from app.config import get_settings
    settings = get_settings()
    if not settings.s3_bucket_name:
        logger.info("S3 not configured — uploads will stay local.")
        return None
    return S3StorageService(
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        bucket_name=settings.s3_bucket_name,
    )
