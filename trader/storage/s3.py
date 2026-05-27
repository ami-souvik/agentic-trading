"""
S3 helpers for archiving raw data and decision logs.

All objects are stored in the bucket configured by S3_BUCKET_NAME env var.
Dry-run mode skips actual writes but logs the intended operation.
"""
from __future__ import annotations

import json
import logging

import boto3
from botocore.exceptions import ClientError

from trader.config.settings import get_settings

logger = logging.getLogger(__name__)


def _s3_client():
    settings = get_settings()
    return boto3.client("s3", region_name=settings.aws_region)


def upload_bytes(s3_key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    settings = get_settings()
    if settings.dry_run:
        logger.debug("[DRY RUN] S3 upload → s3://%s/%s (%d bytes)", settings.s3_bucket_name, s3_key, len(data))
        return

    try:
        _s3_client().put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=data,
            ContentType=content_type,
        )
        logger.info("Uploaded s3://%s/%s", settings.s3_bucket_name, s3_key)
    except ClientError as e:
        logger.error("S3 upload failed for %s: %s", s3_key, e)
        raise


def upload_json(s3_key: str, obj: dict | list) -> None:
    upload_bytes(s3_key, json.dumps(obj, indent=2, default=str).encode(), content_type="application/json")


def upload_text(s3_key: str, text: str) -> None:
    upload_bytes(s3_key, text.encode(), content_type="text/plain")


def download_bytes(s3_key: str) -> bytes:
    settings = get_settings()
    try:
        response = _s3_client().get_object(Bucket=settings.s3_bucket_name, Key=s3_key)
        return response["Body"].read()
    except ClientError as e:
        logger.error("S3 download failed for %s: %s", s3_key, e)
        raise


def key_exists(s3_key: str) -> bool:
    settings = get_settings()
    try:
        _s3_client().head_object(Bucket=settings.s3_bucket_name, Key=s3_key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise
