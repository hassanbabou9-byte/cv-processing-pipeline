"""
MinIO object storage service.

Responsible for storing and retrieving candidate images.

This service is intentionally independent from:
    - CV processing
    - LLM extraction
    - PostgreSQL
    - image extraction

It only handles communication with MinIO.
"""

import io
import logging

from minio import Minio
from minio.error import S3Error

from app.config.settings import Settings

logger = logging.getLogger(__name__)


class MinIOStorage:
    """Client for MinIO object storage."""

    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.minio_bucket

        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    # ============================================================
    # Bucket
    # ============================================================

    def ensure_bucket(self) -> None:
        """
        Create the configured bucket if it does not already exist.
        """

        try:
            if not self._client.bucket_exists(
                self._bucket
            ):
                self._client.make_bucket(
                    self._bucket
                )

                logger.info(
                    "Created MinIO bucket: %s",
                    self._bucket,
                )

        except S3Error:
            logger.exception(
                "Failed to initialize MinIO bucket: %s",
                self._bucket,
            )
            raise

    # ============================================================
    # Upload
    # ============================================================

    def upload_image(
        self,
        object_name: str,
        image_data: bytes,
        content_type: str,
    ) -> str:
        """
        Upload an image to MinIO.

        Parameters
        ----------
        object_name:
            Object key inside the bucket.

            Example:
                candidates/a1000001/photo.png

        image_data:
            Image content as bytes.

        content_type:
            MIME type.

            Example:
                image/png
                image/jpeg

        Returns
        -------
        str
            The MinIO object key.
        """

        if not image_data:
            raise ValueError(
                "Cannot upload an empty image."
            )

        try:
            self.ensure_bucket()

            self._client.put_object(
                bucket_name=self._bucket,
                object_name=object_name,
                data=io.BytesIO(image_data),
                length=len(image_data),
                content_type=content_type,
            )

            logger.info(
                "Candidate image uploaded successfully: %s",
                object_name,
            )

            return object_name

        except S3Error:
            logger.exception(
                "Failed to upload image: %s",
                object_name,
            )
            raise

    # ============================================================
    # Download
    # ============================================================

    def get_image(
        self,
        object_name: str,
    ) -> bytes:
        """
        Retrieve an image from MinIO.

        Returns
        -------
        bytes
            Image content.
        """

        response = None

        try:
            response = self._client.get_object(
                bucket_name=self._bucket,
                object_name=object_name,
            )

            return response.read()

        except S3Error:
            logger.exception(
                "Failed to retrieve image: %s",
                object_name,
            )
            raise

        finally:
            if response is not None:
                response.close()
                response.release_conn()

    # ============================================================
    # Delete
    # ============================================================

    def delete_image(
        self,
        object_name: str,
    ) -> None:
        """
        Delete an image from MinIO.
        """

        try:
            self._client.remove_object(
                bucket_name=self._bucket,
                object_name=object_name,
            )

            logger.info(
                "Candidate image deleted successfully: %s",
                object_name,
            )

        except S3Error:
            logger.exception(
                "Failed to delete image: %s",
                object_name,
            )
            raise

    # ============================================================
    # Existence
    # ============================================================

    def image_exists(
        self,
        object_name: str,
    ) -> bool:
        """
        Check whether an image exists in MinIO.
        """

        try:
            self._client.stat_object(
                bucket_name=self._bucket,
                object_name=object_name,
            )

            return True

        except S3Error as exc:
            if exc.code in {
                "NoSuchKey",
                "NoSuchObject",
                "NotFound",
            }:
                return False

            logger.exception(
                "Failed to check image existence: %s",
                object_name,
            )
            raise