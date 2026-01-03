# producer_fixed.py
from redis import Redis
from rq import Queue, Retry
from rq.job import Job
import time
from typing import Any, Dict, Optional, List
from datetime import timedelta
import logging

class RedisQueueProducer:
    """Fixed Redis Queue Producer with proper retry handling"""
    
    def __init__(
        self, 
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        queue_name: str = 'default'
    ):
        # Connection pooling
        self.redis_conn = Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=False,
            socket_keepalive=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        self.queue = Queue(
            name=queue_name,
            connection=self.redis_conn,
            default_timeout=3600
        )
    
    def push_task(
        self, 
        func: callable,
        *args,
        job_timeout: int = 3600,
        result_ttl: int = 86400,
        failure_ttl: int = 604800,
        max_retries: int = 3,
        retry_intervals: List[int] = None,  # Seconds between retries
        **kwargs
    ) -> str:
        """
        ✅ FIXED: Push task with proper retry configuration
        
        Args:
            func: Function to execute
            max_retries: Number of retry attempts (default: 3)
            retry_intervals: List of wait times between retries in seconds
                            Example: [10, 30, 60] = wait 10s, then 30s, then 60s
                            If None, uses exponential backoff
        
        Returns:  
            job_id: Unique job identifier
        """
        try:
            # ✅ Option 1: Simple retry with max attempts
            if retry_intervals is None:
                retry = Retry(max=max_retries)
            else:
                # ✅ Option 2: Custom retry intervals
                retry = Retry(
                    max=max_retries,
                    interval=retry_intervals
                )
            
            job = self.queue.enqueue(
                func,
                *args,
                job_timeout=job_timeout,
                result_ttl=result_ttl,
                failure_ttl=failure_ttl,
                retry=retry,  # ✅ Pass Retry object, not int
                **kwargs
            )
            
            print(f"✅ Job {job.id} enqueued with {max_retries} retries")
            return job.id
            
        except Exception as e:  
            print(f"❌ Failed to enqueue task: {e}")
            raise
    
    def push_task_no_retry(
        self,
        func: callable,
        *args,
        **kwargs
    ) -> str:
        """Push task without retry (fail immediately)"""
        job = self.queue.enqueue(
            func,
            *args,
            retry=None,  # ✅ No retry
            **kwargs
        )
        return job.id
    
    def push_task_with_exponential_backoff(
        self,
        func: callable,
        *args,
        max_retries: int = 5,
        initial_delay: int = 1,
        **kwargs
    ) -> str:
        """
        Push task with exponential backoff
        Retries:  1s, 2s, 4s, 8s, 16s... 
        """
        # Calculate exponential intervals
        intervals = [initial_delay * (2 ** i) for i in range(max_retries)]
        
        retry = Retry(max=max_retries, interval=intervals)
        
        job = self.queue.enqueue(
            func,
            *args,
            retry=retry,
            **kwargs
        )
        
        print(f"✅ Job {job.id} with exponential backoff:  {intervals}")
        return job.id
    
    def push_task_with_custom_intervals(
        self,
        func: callable,
        *args,
        retry_schedule: List[int] = None,  # [10, 30, 60, 300]
        **kwargs
    ) -> str:
        """
        Push task with custom retry schedule
        Example: [10, 30, 60, 300] = retry after 10s, 30s, 1min, 5min
        """
        if retry_schedule is None:
            retry_schedule = [10, 30, 60, 300, 600]  # Default schedule
        
        retry = Retry(
            max=len(retry_schedule),
            interval=retry_schedule
        )
        
        job = self.queue.enqueue(
            func,
            *args,
            retry=retry,
            **kwargs
        )
        
        print(f"✅ Job {job.id} with schedule: {retry_schedule}s")
        return job.id
    
    def push_task_with_priority(
        self,
        func: callable,
        priority: str = 'normal',
        max_retries: int = 3,
        *args,
        **kwargs
    ) -> str:
        """Push task with priority and retry"""
        priority_queues = {
            'critical': Queue('critical', connection=self.redis_conn),
            'high': Queue('high', connection=self.redis_conn),
            'normal': self.queue,
            'low':  Queue('low', connection=self. redis_conn)
        }
        
        queue = priority_queues. get(priority, self.queue)
        
        retry = Retry(max=max_retries) if max_retries > 0 else None
        
        job = queue.enqueue(
            func,
            *args,
            retry=retry,
            **kwargs
        )
        return job.id
    
    def get_job_info(self, job_id: str) -> Dict[str, Any]:
        """Get detailed job information including retry status"""
        try: 
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            return {
                'id': job. id,
                'status': job.get_status(),
                'result': job.result,
                'exc_info': job.exc_info,
                'created_at': job.created_at. isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'ended_at': job.ended_at.isoformat() if job.ended_at else None,
                'retries_left': job. retries_left,  # ✅ Current retries remaining
                'retry_intervals': job.retry_intervals,  # ✅ Retry schedule
                'meta': job.meta  # Custom metadata
            }
        except Exception as e:
            return {'error': str(e)}
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending/queued job"""
        try: 
            job = Job.fetch(job_id, connection=self.redis_conn)
            job.cancel()
            job.delete()
            return True
        except Exception as e:
            print(f"❌ Failed to cancel job: {e}")
            return False
    
    def requeue_failed_job(self, job_id: str, reset_retries: bool = True) -> bool:
        """Manually requeue a failed job"""
        try:
            job = Job. fetch(job_id, connection=self.redis_conn)
            
            if reset_retries: 
                # Reset retry counter
                job.retries_left = job.retry. max if job.retry else 0
            
            # Requeue the job
            self.queue.enqueue_job(job)
            print(f"✅ Job {job_id} requeued")
            return True
            
        except Exception as e: 
            print(f"❌ Failed to requeue:  {e}")
            return False
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        return {
            'queued':  len(self.queue),
            'started': self.queue.started_job_registry.count,
            'finished': self.queue.finished_job_registry.count,
            'failed': self. queue.failed_job_registry. count,
            'deferred': self.queue.deferred_job_registry.count,
            'scheduled': self.queue.scheduled_job_registry.count
        }
    
    def close(self):
        """Clean up connections"""
        self.redis_conn.close()


# ============================================
# Example Task Functions
# ============================================

def flaky_task(task_id: int, fail_probability: float = 0.5):
    """
    Simulates a flaky task that sometimes fails
    Good for testing retry logic
    """
    import random
    import time
    
    print(f"🔄 Executing flaky_task {task_id}")
    logging.info(f"🔄 Executing flaky_task {task_id}")
    time.sleep(1)
    
    logging.info(f"Task {task_id} sleeping for 1 second")

    # if random.random() < fail_probability:
    #     raise Exception(f"Task {task_id} failed randomly!")
    
    print(f"✅ Task {task_id} succeeded")
    return {"task_id": task_id, "status": "success"}


def api_call_with_rate_limit(endpoint: str, retry_count: int = 0):
    """
    Simulates API call that might hit rate limits
    """
    import random
    import time
    
    print(f"📡 Calling {endpoint} (attempt {retry_count + 1})")
    time.sleep(0.5)
    
    # Simulate rate limit
    if random.random() < 0.3: 
        raise Exception(f"Rate limit exceeded for {endpoint}")
    
    return {"endpoint": endpoint, "status":  "success", "attempts": retry_count + 1}


def process_streaming_batch(batch_id: int, records: List[Dict]):
    """
    Process streaming data batch with occasional failures
    """
    import random
    import time
    
    print(f"📦 Processing batch {batch_id} with {len(records)} records")
    time.sleep(2)
    
    # Simulate network issues
    if random.random() < 0.2:
        raise ConnectionError(f"Network error processing batch {batch_id}")
    
    # Simulate data validation errors
    if random.random() < 0.1:
        raise ValueError(f"Invalid data in batch {batch_id}")
    
    return {
        "batch_id": batch_id,
        "processed_count": len(records),
        "status": "success"
    }


# ============================================
# Example Usage & Testing
# ============================================

if __name__ == "__main__": 
    import time
    
    # Initialize producer
    producer = RedisQueueProducer(
        redis_host='localhost',
        redis_port=6379,
        queue_name='data_pipeline'
    )
    
    print("=" * 60)
    print("🚀 Redis Queue Producer - Retry Examples")
    print("=" * 60)
    
    # Example 1: Simple retry (3 attempts)
    print("\n1️⃣ Simple retry with 3 max attempts")
    job1 = producer.push_task(
        flaky_task,
        task_id=1,
        fail_probability=0.7,
        max_retries=3,
        job_timeout=30
    )
    
    # Example 2: No retry (fail immediately)
    print("\n2️⃣ No retry - fail immediately")
    job2 = producer.push_task_no_retry(
        flaky_task,
        task_id=2,
        fail_probability=0.9
    )
    
    # Example 3: Exponential backoff
    print("\n3️⃣ Exponential backoff (1s, 2s, 4s, 8s, 16s)")
    job3 = producer.push_task_with_exponential_backoff(
        api_call_with_rate_limit,
        endpoint="https://api.example.com/data",
        max_retries=5,
        initial_delay=1
    )
    
    # Example 4: Custom retry schedule
    print("\n4️⃣ Custom retry schedule (10s, 30s, 60s, 5min)")
    job4 = producer.push_task_with_custom_intervals(
        process_streaming_batch,
        batch_id=100,
        records=[{"id": i} for i in range(50)],
        retry_schedule=[10, 30, 60, 300]
    )
    
    # Example 5: Priority with retry
    print("\n5️⃣ High priority with 5 retries")
    job5 = producer.push_task_with_priority(
        flaky_task,
        priority='high',
        max_retries=5,
        task_id=5,
        fail_probability=0.8
    )
    
    # Wait a bit for jobs to be processed
    print("\n⏳ Waiting for jobs to process...")
    time.sleep(3)
    
    # Check job statuses
    print("\n" + "=" * 60)
    print("📊 Job Status Summary")
    print("=" * 60)
    
    for idx, job_id in enumerate([job1, job2, job3, job4, job5], 1):
        info = producer.get_job_info(job_id)
        print(f"\nJob {idx} ({job_id[: 8]}...):")
        print(f"  Status: {info. get('status')}")
        print(f"  Retries left: {info.get('retries_left')}")
        print(f"  Retry intervals: {info.get('retry_intervals')}")
        if info.get('exc_info'):
            print(f"  Error: {info. get('exc_info')[:100]}...")
    
    # Queue statistics
    print("\n" + "=" * 60)
    print("📈 Queue Statistics")
    print("=" * 60)
    stats = producer.get_queue_stats()
    for key, value in stats.items():
        print(f"  {key. capitalize()}: {value}")
    
    # Example:  Requeue failed job
    print("\n" + "=" * 60)
    print("🔄 Testing Manual Requeue")
    print("=" * 60)
    time.sleep(5)  # Wait for some failures
    
    # Find and requeue failed jobs
    from rq.registry import FailedJobRegistry
    
    failed_registry = FailedJobRegistry(queue=producer.queue)
    failed_job_ids = failed_registry.get_job_ids()
    
    if failed_job_ids:
        print(f"\n❌ Found {len(failed_job_ids)} failed jobs")
        for failed_id in failed_job_ids[: 3]:  # Requeue first 3
            print(f"  Requeuing {failed_id[: 8]}...")
            producer.requeue_failed_job(failed_id, reset_retries=True)
    else:
        print("\n✅ No failed jobs found")
    
    producer.close()
    print("\n✅ Done!")