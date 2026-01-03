# consumer.py
from redis import Redis
from rq import Worker, Queue
from typing import List, Optional,Dict
import signal
import sys
import logging
from JobDetailCrawler.beautifulsoup_utils import JobDetailCrawler
from crawl_job_detail_task import crawl_job_detail_task
# Configure logging
logging.basicConfig(
    level=logging. INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedisQueueConsumer: 
    """Best practice Redis Queue Consumer/Worker"""
    
    def __init__(
        self,
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        queue_names: List[str] = None,
        worker_name: Optional[str] = None
    ):
        if queue_names is None:
            queue_names = ['default']
        
        # Redis connection with pooling
        self.redis_conn = Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=False,
            socket_keepalive=True,
            health_check_interval=30
        )
        
        # Create queue objects
        self.queues = [
            Queue(name, connection=self.redis_conn) 
            for name in queue_names
        ]
        
        self.worker_name = worker_name
        self.worker = None
    
    def start_worker(
        self,
        burst: bool = False,  # True = process existing jobs and exit
        num_workers: int = 1,
        max_jobs: Optional[int] = None
    ):
        """Start consuming tasks from queue"""
        
        # Create worker
        self.worker = Worker(
            self.queues,
            connection=self.redis_conn,
            name=self.worker_name,
            log_job_description=True,
            job_monitoring_interval=5
        )
        
        # Graceful shutdown handler
        def signal_handler(signum, frame):
            logger. info("🛑 Received shutdown signal, stopping worker...")
            if self.worker:
                self. worker.request_stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start worker
        logger.info(f"🚀 Starting worker for queues: {[q.name for q in self. queues]}")
        
        try:
            self.worker.work(
                burst=burst,
                max_jobs=max_jobs,
                with_scheduler=True  # Enable scheduled jobs
            )
        except Exception as e:
            logger.error(f"❌ Worker error: {e}")
            raise
    
    def close(self):
        """Clean up connections"""
        if self.redis_conn:
            self.redis_conn.close()


# Task handlers module (separate file recommended)
# tasks.py
def process_streaming_data(batch_id: int, records: List[Dict]) -> Dict:
    """Example:  Process streaming data batch"""
    import time
    import random
    
    logger = logging.getLogger(__name__)
    logger.info(f"📦 Processing batch {batch_id} with {len(records)} records")
    
    # Simulate processing
    time. sleep(random.uniform(1, 3))
    
    # Simulate occasional failures
    if random.random() < 0.1:  # 10% failure rate
        raise Exception(f"Processing failed for batch {batch_id}")
    
    processed = len(records)
    logger.info(f"✅ Successfully processed {processed} records")
    
    return {
        "batch_id": batch_id,
        "processed_count": processed,
        "status": "success"
    }


def transform_data(data: Dict, transformation_type: str) -> Dict:
    """Example: Transform data"""
    logger = logging.getLogger(__name__)
    logger.info(f"🔄 Transforming data with type: {transformation_type}")
    
    # Your transformation logic
    transformed = {
        **data,
        "transformed":  True,
        "transformation_type": transformation_type
    }
    
    return transformed


# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Redis Queue Worker')
    parser.add_argument('--queues', nargs='+', default=['default'],
                        help='Queue names to listen to')
    parser.add_argument('--burst', action='store_true',
                        help='Process existing jobs and exit')
    parser.add_argument('--worker-name', type=str, default=None,
                        help='Worker name')
    
    args = parser.parse_args()
    
    # Initialize consumer
    consumer = RedisQueueConsumer(
        redis_host='redis',
        redis_port=6379,
        queue_names=['job-queue'],
        worker_name=args.worker_name
    )
    
    # Start worker (blocking call)
    consumer.start_worker(burst=False)