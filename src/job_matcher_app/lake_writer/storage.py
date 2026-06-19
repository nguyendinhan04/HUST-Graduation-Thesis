from __future__ import annotations

import json
import logging
from io import BytesIO

import boto3
from botocore.exceptions import ClientError

from job_matcher_app.lake_writer.settings import LakeWriterSettings


logger = logging.getLogger(__name__)


class MinioObjectStorage:
    def __init__(self, settings: LakeWriterSettings):
        self.settings = settings
        self.client = boto3.client(
            "s3",
            endpoint_url=f"http{'s' if settings.minio_secure else ''}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name="us-east-1",
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.settings.lake_bucket)
        except ClientError as exc:
            status_code = int(exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0))
            if status_code not in {404, 403}:
                raise
            logger.info("Creating lake bucket %s", self.settings.lake_bucket)
            self.client.create_bucket(Bucket=self.settings.lake_bucket)

    def put_bytes(self, object_name: str, data: bytes, content_type: str) -> None:
        self.ensure_bucket()
        self.client.put_object(
            Bucket=self.settings.lake_bucket,
            Key=object_name,
            Body=BytesIO(data),
            ContentType=content_type,
        )

    def get_bytes(self, object_name: str) -> bytes:
        response = self.client.get_object(Bucket=self.settings.lake_bucket, Key=object_name)
        return response["Body"].read()

    def list_parquet_keys(self, prefix: str) -> list[str]:
        keys: list[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.settings.lake_bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                key = item.get("Key")
                if key and key.endswith(".parquet"):
                    keys.append(key)
        return keys

    def put_json(self, object_name: str, payload: dict[str, object]) -> None:
        self.put_bytes(
            object_name,
            json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
            content_type="application/json",
        )
