import json
import logging
import os
import sys
import time
from datetime import datetime
import boto3

from redis import Redis
from redis.exceptions import ResponseError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

STREAM_NAME = os.getenv("TELEMETRY_STREAM_NAME", "ner_telemetry_stream")
GROUP_NAME = os.getenv("TELEMETRY_GROUP_NAME", "telemetry_group")
CONSUMER_NAME = os.getenv("TELEMETRY_CONSUMER_NAME", "worker_1")
FLUSH_INTERVAL_SECONDS = int(os.getenv("TELEMETRY_FLUSH_INTERVAL", "60"))
TEMP_DIR = os.getenv("TELEMETRY_TEMP_DIR", "/app/src/telemetry_temp")
CURRENT_FILE_PATH = os.path.join(TEMP_DIR, "ner_logs.jsonl")


def get_redis_client() -> Redis:
    return Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        password=os.getenv("REDIS_PASSWORD", None),
        decode_responses=True,
        socket_keepalive=True,
        health_check_interval=30,
        socket_timeout=30, # ensure socket timeout is larger than the block time (5s)
    )


def get_s3_client():
    endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "ROOTUSER")
    secret_key = os.getenv("MINIO_SECRET_KEY", "1234567890")
    secure = os.getenv("MINIO_SECURE", "false").lower() in {"1", "true", "yes"}

    return boto3.client(
        "s3",
        endpoint_url=f"http{'s' if secure else ''}://{endpoint}",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )


def ensure_consumer_group(redis_client: Redis):
    try:
        redis_client.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
        logger.info(f"Created consumer group {GROUP_NAME} on stream {STREAM_NAME}")
    except ResponseError as e:
        if "BUSYGROUP Consumer Group name already exists" in str(e):
            logger.info(f"Consumer group {GROUP_NAME} already exists.")
        else:
            raise e


def process_event(message_id: str, payload: dict):
    os.makedirs(TEMP_DIR, exist_ok=True)
    with open(CURRENT_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    logger.debug(f"Appended message {message_id} to temp file")


def flush_to_minio(s3_client):
    if not os.path.exists(CURRENT_FILE_PATH) or os.path.getsize(CURRENT_FILE_PATH) == 0:
        return

    bucket_name = os.getenv("TELEMETRY_MINIO_BUCKET", "telemetry")
    
    # Ensure bucket exists
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except Exception as e:
        # If it throws 404, the bucket does not exist
        if hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == '404':
            try:
                s3_client.create_bucket(Bucket=bucket_name)
                logger.info(f"Created bucket {bucket_name} in MinIO")
            except Exception as create_error:
                logger.error(f"Failed to create bucket {bucket_name}: {create_error}")
                return
        else:
            logger.error(f"Failed to check bucket {bucket_name}: {e}")
            return

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp_str = now.strftime("%H%M%S")
    object_key = f"telemetry/ner/{date_str}/logs_{timestamp_str}.jsonl"

    try:
        s3_client.upload_file(CURRENT_FILE_PATH, bucket_name, object_key)
        logger.info(f"Successfully uploaded {CURRENT_FILE_PATH} to s3://{bucket_name}/{object_key}")
        # Clear the file after successful upload
        os.remove(CURRENT_FILE_PATH)
    except Exception as e:
        logger.error(f"Failed to upload to MinIO: {e}")


def start_worker():
    redis_client = get_redis_client()
    ensure_consumer_group(redis_client)
    s3_client = get_s3_client()

    logger.info("Starting telemetry worker, listening for events...")
    last_flush_time = time.time()
    
    # Process pending messages first
    while True:
        try:
            pending_streams = redis_client.xreadgroup(
                groupname=GROUP_NAME,
                consumername=CONSUMER_NAME,
                streams={STREAM_NAME: "0"},
                count=50,
                block=0
            )
            if not pending_streams or not pending_streams[0][1]:
                break
                
            stream_name, messages = pending_streams[0]
            for message_id, payload in messages:
                process_event(message_id, payload)
                redis_client.xack(STREAM_NAME, GROUP_NAME, message_id)
        except Exception as e:
            logger.error(f"Error processing pending messages: {e}")
            time.sleep(5)
            
    # Process new messages
    while True:
        try:
            streams = redis_client.xreadgroup(
                groupname=GROUP_NAME,
                consumername=CONSUMER_NAME,
                streams={STREAM_NAME: ">"},
                count=50,
                block=5000
            )

            if streams:
                stream_name, messages = streams[0]
                for message_id, payload in messages:
                    process_event(message_id, payload)
                    redis_client.xack(STREAM_NAME, GROUP_NAME, message_id)
            
            # Check if it's time to flush
            if time.time() - last_flush_time > FLUSH_INTERVAL_SECONDS:
                flush_to_minio(s3_client)
                last_flush_time = time.time()
                
        except Exception as e:
            logger.error(f"Error processing stream: {e}")
            time.sleep(5)


if __name__ == "__main__":
    start_worker()
