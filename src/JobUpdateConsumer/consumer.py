import signal
import sys
import json
import time
import datetime
from confluent_kafka import Consumer
from MinioClient.MinioClient import MinioClient
from JobDetailCrawler.beautifulsoup_utils import crawl_list_job

running = True

def handle_sigterm(signum, frame):
    global running
    print("Received stop signal, shutting down gracefully...")
    running = False

signal.signal(signal.SIGINT, handle_sigterm)
signal.signal(signal.SIGTERM, handle_sigterm)

class BronzeLayerConsumer:
    def on_assign(self, consumer, partitions):
        print(f"Consumer assigned to partitions: {partitions}")
        consumer.assign(partitions)

    def __init__(self, topic, batch_size=10, flush_interval=10):
        self.conf = {
            'bootstrap.servers': 'kafka:29092',
            'group.id': 'job-update-consumer-bronze',
            'auto.offset.reset': 'earliest'
        }
        self.consumer = Consumer(self.conf)
        self.consumer.subscribe([topic], on_assign=self.on_assign)
        self.topic = topic
        
        self.minio_client = MinioClient()
        self.bucket_name = "bronze-layer"
        
        self.buffer = []
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.last_flush_time = time.time()

    def flush_buffer(self):
        if not self.buffer:
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        date_path = datetime.datetime.now().strftime("year=%Y/month=%m/day=%d")
        object_name = f"{self.topic}/{date_path}/{timestamp}_{len(self.buffer)}.jsonl"
        
        # Convert buffer to newline-delimited JSON string
        # data_str = "\n".join([json.dumps(msg) for msg in self.buffer])
        detail_jobs = crawl_list_job(self.buffer, datetime.datetime.now().isoformat())
        data_str = "\n".join([json.dumps(job, ensure_ascii=False) for job in detail_jobs])
        
        print(f"Flushing {len(self.buffer)} messages to MinIO: {object_name}")
        try:
            self.minio_client.put_object(self.bucket_name, object_name, data_str)
            self.buffer = []
            self.last_flush_time = time.time()
        except Exception as e:
            print(f"Error flushing to MinIO: {e}")
            # In a real app, you might want to retry or DLQ here
            pass

    def run(self):
        print(f"Bronze Layer Consumer started for topic: {self.topic}")
        try:
            while running:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    # Check if we need to flush based on time
                    if time.time() - self.last_flush_time > self.flush_interval and self.buffer:
                        self.flush_buffer()
                    continue
                
                if msg.error():
                    print(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    print(f"Received message from partition: {msg.partition()}")
                    value = msg.value().decode('utf-8')
                    # Try to parse JSON to ensure validity, or just store raw string
                    try:
                        json_value = json.loads(value)
                        self.buffer.append(json_value)
                    except json.JSONDecodeError:
                        # If not JSON, wrap it
                        self.buffer.append({"raw_content": value, "timestamp": time.time()})
                        
                    if len(self.buffer) >= self.batch_size:
                        self.flush_buffer()
                        
                except Exception as e:
                    print(f"Error processing message: {e}")

        finally:
            # Flush remaining messages
            self.flush_buffer()
            self.consumer.close()
            print("Consumer closed gracefully.")
            sys.exit(0)

if __name__ == "__main__":
    # You can configure topic via env var or args
    TOPIC = 'job-updates' # Replace with your actual topic
    consumer = BronzeLayerConsumer(topic=TOPIC)
    consumer.run()