import signal
import sys
import json
import time
import datetime
from confluent_kafka import Consumer
from MinioClient.MinioClient import MinioClient
from JobDetailCrawler.beautifulsoup_utils import JobDetailCrawler
from JobDBClient.JobDBPostgreClient import JobDBPostgreClient
from typing import List, Dict

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

    def __init__(self, topic, batch_size=10, flush_interval=100):
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
        p_total = datetime.datetime.now()
        if not self.buffer or len(self.buffer) == 0:
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        date_path = datetime.datetime.now().strftime("year=%Y/month=%m/day=%d")
        object_name = f"{self.topic}/{date_path}/{timestamp}_{len(self.buffer)}.jsonl"
        

        job_crawler = JobDetailCrawler()
        job_db_client = JobDBPostgreClient()

        detail_jobs = []
        print(f"Processing {len(self.buffer)} jobs for detail crawling...")
        for job in self.buffer:
            print(f"Crawling detail for job: {job.get('job_url')}")
            print("job-data:", job)
            try:
                p1 = datetime.datetime.now()
                job_detail = job_crawler.crawl_job_detail(job)
                detail_jobs.append(job_detail)
                p2 = datetime.datetime.now()
                job_db_client.update_job_last_crawl(
                    job_detail.get("url_hash"), 
                    job_detail.get("job_url"), 
                    job_detail.get("detail_title"), 
                    datetime.datetime.now()
                )
                p3 = datetime.datetime.now()
                print(f"Crawled detail for job: {job.get('job_url')} in {(p2 - p1).total_seconds()}s, DB update took {(p3 - p2).total_seconds()}s")
            except Exception as e:
                print(f"[ERROR] Lỗi khi crawl chi tiết job {job.get('job_url')}: {e}")


        data_str = "\n".join([json.dumps(job, ensure_ascii=False) for job in detail_jobs])
        
        print(f"Flushing {len(self.buffer)} messages to MinIO: {object_name}")
        try:
            p4 = datetime.datetime.now()
            self.minio_client.put_object(self.bucket_name, object_name, data_str)
            p5 = datetime.datetime.now()
            print(f"Flushed to MinIO in {(p5 - p4).total_seconds()}s")
        except Exception as e:
            print(f"Error flushing to MinIO: {e}")
            # In a real app, you might want to retry or DLQ here
        finally:
            self.buffer = []
            self.last_flush_time = time.time()
            job_db_client.close()
            p_total_end = datetime.datetime.now()
            print(f"Total flush processing time: {(p_total_end - p_total).total_seconds()}s")

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
                        json_value.update({"datetime": datetime.datetime.now().isoformat()})
                        self.buffer.append(json_value)
                    except json.JSONDecodeError:
                        # If not JSON, wrap it
                        # self.buffer.append({"raw_content": value, "timestamp": time.time()})
                        print("[WARNING] Received non-JSON message, skipping.")
                        
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