import logging
from typing import Optional

from botocore.exceptions import ClientError

from config.settings import S3_BUCKET_NAME, S3_SIGNED_URL_TTL_SECONDS
from lib.aws_s3 import aws_s3_client

logger = logging.getLogger(__name__)


class S3Service:
    """
    S3 Service for verifying object existence and generating secure presigned URLs.
    Does not expose raw storage paths or secret credentials.
    """

    def __init__(
        self,
        client=aws_s3_client,
        bucket_name: Optional[str] = S3_BUCKET_NAME,
        default_ttl: int = S3_SIGNED_URL_TTL_SECONDS,
    ):
        self._client = client
        self._bucket_name = bucket_name
        self._default_ttl = default_ttl

    def generate_presigned_url(
        self,
        s3_key: Optional[str],
        expires_in: Optional[int] = None,
    ) -> Optional[str]:
        """
        Generates a secure, temporary presigned GET URL for a given document's S3 key.
        Returns None gracefully if the key is missing, S3 is unconfigured, or an error occurs.
        """
        if not s3_key or not isinstance(s3_key, str) or not s3_key.strip():
            return None

        if not self._bucket_name or self._client is None:
            logger.warning("S3 bucket or client is not configured; cannot generate presigned URL.")
            return None

        ttl = expires_in or self._default_ttl
        try:
            url = self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self._bucket_name,
                    "Key": s3_key.strip(),
                },
                ExpiresIn=ttl,
            )
            return url
        except (ClientError, Exception) as e:
            logger.warning(f"Failed to generate presigned URL for S3 key '{s3_key}': {e}")
            return None

    def verify_object_exists(self, s3_key: Optional[str]) -> bool:
        """
        Checks if an S3 object exists in the configured bucket without downloading it.
        """
        if not s3_key or not self._bucket_name or self._client is None:
            return False

        try:
            self._client.head_object(
                Bucket=self._bucket_name,
                Key=s3_key.strip(),
            )
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in {"404", "NoSuchKey"}:
                return False
            logger.warning(f"S3 head_object error for key '{s3_key}': {e}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error checking S3 key '{s3_key}': {e}")
            return False
