
# --- RS256 JWT Asymmetric Engine ---
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

logger = logging.getLogger("JWTEngine")

class JWTEngine:
    """
    A highly secure, enterprise-grade JWT engine utilizing RS256 (RSA Signature with SHA-256).
    Supports asymmetric key pairs (Private key signs, Public key verifies).
    Includes infrastructure for key rotation via 'kid' (Key ID) headers and JWKS generation.
    """

    def __init__(self):
        # In production, keys should be loaded from AWS KMS, HashiCorp Vault, or environment variables.
        # For this implementation, we generate an ephemeral key pair for demonstration.
        self.kid = "v1-2024-01-01"
        self._private_key, self._public_key = self._generate_keypair()
        self.algorithm = "RS256"
        self.issuer = "https://auth.envforage.com"
        self.audience = "https://api.envforage.com"
        self.access_token_expire_minutes = 15
        self.refresh_token_expire_days = 7

    def _generate_keypair(self) -> tuple[bytes, bytes]:
        """Generates an ephemeral 2048-bit RSA key pair."""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem_private = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        pem_public = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem_private, pem_public

    def create_token(self, subject: str, claims: dict[str, Any] | None = None, is_refresh: bool = False) -> str:
        """Generates a signed JWT with standard registered claims (exp, iat, iss, aud, sub)."""
        now = datetime.now(UTC)

        if is_refresh:
            expires_delta = timedelta(days=self.refresh_token_expire_days)
            token_type = "refresh"
        else:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)
            token_type = "access"

        expire = now + expires_delta

        payload = {
            "sub": str(subject),
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "iss": self.issuer,
            "aud": self.audience,
            "type": token_type
        }

        if claims:
            # Ensure we don't overwrite registered claims
            safe_claims = {k: v for k, v in claims.items() if k not in payload}
            payload.update(safe_claims)

        encoded_jwt = jwt.encode(
            payload,
            self._private_key,
            algorithm=self.algorithm,
            headers={"kid": self.kid}
        )
        return encoded_jwt

    def decode_token(self, token: str) -> dict[str, Any]:
        """Verifies the JWT signature using the public key and validates all registered claims."""
        try:
            # First, inspect the header unverified to find the 'kid'
            unverified_headers = jwt.get_unverified_header(token)
            kid = unverified_headers.get("kid")

            if kid != self.kid:
                # In a real system, we'd fetch the public key matching the 'kid'
                logger.warning(f"Unknown Key ID (kid): {kid}")
                raise jwt.InvalidKeyError("Key ID not found in JWKS")

            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer
            )
            return payload

        except jwt.ExpiredSignatureError:
            logger.debug("Token has expired")
            raise Exception("Token has expired")
        except jwt.PyJWTError as e:
            logger.debug(f"JWT Validation failed: {e}")
            raise Exception(f"Invalid token: {e}")

    def get_jwks(self) -> dict[str, Any]:
        """Generates the JSON Web Key Set (JWKS) for exposing public keys."""
        # Simulated JWKS output
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "alg": self.algorithm,
                    "use": "sig",
                    "kid": self.kid,
                    "n": "simulated_modulus_base64",
                    "e": "AQAB"
                }
            ]
        }
