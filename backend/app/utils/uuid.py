
# --- UUID v7 & v4 Generator ---
import logging
import os
import time
import uuid

logger = logging.getLogger("UUIDGenerator")

class UUIDManager:
    """
    Advanced UUID generator supporting standard v4 and sequential v7.
    UUIDv7 encodes a Unix timestamp in the leading 48 bits, providing
    excellent chronological sorting and B-Tree locality for database indexes,
    eliminating the fragmentation issues of random UUIDv4s.
    """

    @staticmethod
    def generate_v4() -> str:
        """Generates a standard random UUIDv4."""
        return str(uuid.uuid4())

    @staticmethod
    def generate_v7() -> str:
        """
        Generates a sequential UUIDv7.
        (Using a standard bit-shifting algorithm to embed milliseconds).
        """
        try:
            # Get current time in milliseconds
            timestamp_ms = int(time.time() * 1000)

            # The 48-bit timestamp
            timestamp_bytes = timestamp_ms.to_bytes(6, byteorder="big")

            # The remaining 80 bits are random
            random_bytes = os.urandom(10)

            # Combine them
            uuid_bytes = bytearray(timestamp_bytes + random_bytes)

            # Set the version (7) and variant (RFC 4122)
            uuid_bytes[6] = (uuid_bytes[6] & 0x0F) | 0x70 # Version 7
            uuid_bytes[8] = (uuid_bytes[8] & 0x3F) | 0x80 # Variant

            return str(uuid.UUID(bytes=bytes(uuid_bytes)))
        except Exception as e:
            logger.error(f"Failed to generate UUIDv7: {e}. Falling back to v4.")
            return UUIDManager.generate_v4()

    @staticmethod
    def validate(uuid_string: str) -> bool:
        """Validates if a given string is a correctly formatted UUID."""
        try:
            val = uuid.UUID(uuid_string, version=None)
            return str(val) == uuid_string.lower()
        except ValueError:
            return False

    @staticmethod
    def extract_timestamp_v7(uuid_v7_string: str) -> float | None:
        """Extracts the original Unix timestamp (seconds) from a UUIDv7."""
        try:
            u = uuid.UUID(uuid_v7_string)
            if u.version != 7:
                return None

            # Extract the first 6 bytes (48 bits)
            timestamp_bytes = u.bytes[:6]
            timestamp_ms = int.from_bytes(timestamp_bytes, byteorder="big")

            return timestamp_ms / 1000.0
        except Exception:
            return None
