# advanced_producer.py
from redis import Redis
from rq import Queue
from rq.job import Job
from typing import Any, Dict, List, Optional, Callable
import json
import logging
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)


def with_retry(max_retries: int = 3, delay: int = 5):
    """Decorator for retry logic"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    import time
                    time.sleep(delay)
        return wrapper
    return decorator


class AdvancedRedisQueue:
    """Advanced Redis Queue with monitoring and error handling"""
    
    def __init__(self, redis_url: str = 'redis://localhost:6379/0'):
        self.redis_conn = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_keepalive=True,
            health_check_interval=30
        )
        self.queues = {
            'critical': Queue('critical', connection=self.redis_conn),
            'high': Queue('high', connection=self.redis_conn),
            'normal': Queue('normal', connection=self.redis_conn),
            'low': Queue('low', connection=self.redis_conn)
        }
    
    @with_retry(max_retries=3)
    def enqueue_with_callback(
        self,
        func: Callable,
        priority: str = 'normal',
        on_success: Optional[Callable] = None,
        on_failure: Optional[Callable] = None,
        *args,
        **kwargs
    ) -> str:
        """Enqueue task with success/failure callbacks"""
        queue = self.queues. get(priority, self.queues['normal'])
        
        job = queue.enqueue(
            func,
            *args,
            on_success=on_success,
            on_failure=on_failure,
            **kwargs
        )
        
        # Store metadata
        self._store_job_metadata(job. id, {
            'function': func.__name__,
            'priority': priority,
            'enqueued_at': datetime.now().isoformat(),
            'args': str(args),
            'kwargs':  str(kwargs)
        })
        
        logger.info(f"✅ Job {job.id} enqueued to {priority} queue")
        return job.id
    
    def enqueue_batch(
        self,
        tasks: List[Dict[str, Any]],
        priority: str = 'normal'
    ) -> List[str]:
        """Enqueue multiple tasks efficiently"""
        queue = self.queues.get(priority, self.queues['normal'])
        job_ids = []
        
        with queue.connection. pipeline() as pipe:
            for task in tasks:
                job = queue.enqueue(
                    task['func'],
                    *task. get('args', []),
                    **task.get('kwargs', {}),
                    pipeline=pipe
                )
                job_ids.append(job.id)
            pipe.execute()
        
        logger.info(f"✅ Enqueued {len(job_ids)} tasks to {priority} queue")
        return job_ids
    
    def _store_job_metadata(self, job_id:  str, metadata: Dict):
        """Store job metadata for monitoring"""
        key = f"job_metadata:{job_id}"
        self.redis_conn.setex(
            key,
            timedelta(days=7),
            json.dumps(metadata)
        )
    
    def get_job_metadata(self, job_id: str) -> Optional[Dict]:
        """Retrieve job metadata"""
        key = f"job_metadata:{job_id}"
        data = self. redis_conn.get(key)
        return json.loads(data) if data else None
    
    def get_queue_health(self) -> Dict[str, Any]:
        """Get health metrics for all queues"""
        health = {}
        
        for priority, queue in self.queues. items():
            health[priority] = {
                'queued': len(queue),
                'started': queue.started_job_registry.count,
                'finished':  queue.finished_job_registry. count,
                'failed': queue.failed_job_registry.count,
                'workers': len(Worker.all(connection=self.redis_conn))
            }
        
        return health
    
    def cleanup_old_jobs(self, days:  int = 7):
        """Clean up old finished/failed jobs"""
        cutoff = datetime.now() - timedelta(days=days)
        
        for queue in self.queues.values():
            # Clean finished jobs
            for job_id in queue.finished_job_registry. get_job_ids():
                try:
                    job = Job. fetch(job_id, connection=self.redis_conn)
                    if job.ended_at and job.ended_at < cutoff:
                        job.delete()
                except: 
                    pass
            
            # Clean failed jobs
            for job_id in queue.failed_job_registry.get_job_ids():
                try:
                    job = Job.fetch(job_id, connection=self.redis_conn)
                    if job. ended_at and job.ended_at < cutoff:
                        job.delete()
                except:
                    pass
        
        logger.info(f"🧹 Cleaned up jobs older than {days} days")


# Callback functions
def on_task_success(job, connection, result, *args, **kwargs):
    """Called when task succeeds"""
    logger.info(f"✅ Job {job.id} succeeded with result: {result}")
    # Send notification, update database, etc. 


def on_task_failure(job, connection, type, value, traceback):
    """Called when task fails"""
    logger.error(f"❌ Job {job.id} failed: {value}")
    # Send alert, retry logic, etc.


# Example usage
if __name__ == "__main__":
    queue_manager = AdvancedRedisQueue()
    
    # Single task with callbacks
    job_id = queue_manager.enqueue_with_callback(
        process_streaming_data,
        priority='high',
        on_success=on_task_success,
        on_failure=on_task_failure,
        batch_id=1,
        records=[{"id": i} for i in range(100)]
    )
    
    # Batch enqueue
    tasks = [
        {
            'func': transform_data,
            'args':  ({'data': f'record_{i}'},),
            'kwargs': {'transformation_type': 'normalize'}
        }
        for i in range(10)
    ]
    job_ids = queue_manager.enqueue_batch(tasks, priority='normal')
    
    # Monitor health
    health = queue_manager.get_queue_health()
    print(f"📊 Queue Health: {json.dumps(health, indent=2)}")
    
    # Cleanup
    queue_manager.cleanup_old_jobs(days=7)







# low_level_redis_queue.py
import redis
import json
import uuid
import time
from typing import Any, Dict, Optional, Callable
from datetime import datetime
import pickle


class RedisTaskQueue:
    """Low-level Redis queue implementation"""
    
    def __init__(
        self,
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0,
        queue_name: str = 'tasks'
    ):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=False  # For pickle
        )
        self.queue_name = queue_name
        self.processing_queue = f"{queue_name}:processing"
        self.results_key = f"{queue_name}: results"
    
    def push(
        self,
        task_func: Callable,
        *args,
        priority: int = 0,
        **kwargs
    ) -> str:
        """Push task to queue"""
        task_id = str(uuid.uuid4())
        
        task_data = {
            'id': task_id,
            'func': pickle.dumps(task_func),
            'args': pickle.dumps(args),
            'kwargs': pickle.dumps(kwargs),
            'created_at': datetime.now().isoformat(),
            'priority':  priority
        }
        
        # Use sorted set for priority queue
        self.redis_client.zadd(
            self.queue_name,
            {pickle.dumps(task_data): -priority}  # Negative for high priority first
        )
        
        return task_id
    
    def pull(self, timeout: int = 0) -> Optional[Dict]:
        """Pull task from queue (blocking)"""
        # ZPOPMIN for getting highest priority
        if timeout > 0:
            result = self.redis_client.bzpopmin(self.queue_name, timeout=timeout)
        else:
            result = self.redis_client.zpopmin(self.queue_name, count=1)
        
        if not result:
            return None
        
        if timeout > 0:
            _, task_bytes, _ = result
        else:
            task_bytes, _ = result[0]
        
        task_data = pickle.loads(task_bytes)
        
        # Move to processing queue
        self.redis_client.hset(
            self.processing_queue,
            task_data['id'],
            pickle.dumps(task_data)
        )
        
        return task_data
    
    def execute_task(self, task_data: Dict) -> Any:
        """Execute the pulled task"""
        func = pickle.loads(task_data['func'])
        args = pickle.loads(task_data['args'])
        kwargs = pickle.loads(task_data['kwargs'])
        
        try:
            result = func(*args, **kwargs)
            self.store_result(task_data['id'], result, 'success')
            return result
        except Exception as e:
            self.store_result(task_data['id'], str(e), 'failed')
            raise
        finally:
            # Remove from processing queue
            self.redis_client.hdel(self.processing_queue, task_data['id'])
    
    def store_result(self, task_id: str, result: Any, status: str):
        """Store task result"""
        result_data = {
            'task_id': task_id,
            'result': pickle.dumps(result),
            'status': status,
            'completed_at': datetime.now().isoformat()
        }
        
        self.redis_client. hset(
            self.results_key,
            task_id,
            pickle.dumps(result_data)
        )
        
        # Set TTL
        self.redis_client.expire(f"{self.results_key}:{task_id}", 86400)  # 24 hours
    
    def get_result(self, task_id: str, timeout: int = None) -> Optional[Any]:
        """Get task result (with optional blocking)"""
        if timeout: 
            start = time.time()
            while time.time() - start < timeout:
                result = self.redis_client.hget(self.results_key, task_id)
                if result:
                    result_data = pickle.loads(result)
                    return pickle.loads(result_data['result'])
                time.sleep(0.1)
            return None
        else:
            result = self.redis_client. hget(self.results_key, task_id)
            if result:
                result_data = pickle.loads(result)
                return pickle.loads(result_data['result'])
            return None
    
    def queue_size(self) -> int:
        """Get queue size"""
        return self.redis_client.zcard(self.queue_name)
    
    def clear_queue(self):
        """Clear all queues"""
        self.redis_client.delete(self.queue_name)
        self.redis_client.delete(self.processing_queue)
        self.redis_client.delete(self.results_key)


# Worker implementation
class TaskWorker:
    """Worker to process tasks"""
    
    def __init__(self, queue:  RedisTaskQueue, worker_id: str = None):
        self.queue = queue
        self.worker_id = worker_id or str(uuid.uuid4())
        self.running = False
    
    def start(self, max_tasks: Optional[int] = None):
        """Start processing tasks"""
        self.running = True
        processed = 0
        
        print(f"🚀 Worker {self.worker_id} started")
        
        while self. running:
            if max_tasks and processed >= max_tasks:
                break
            
            # Pull task (block for 1 second)
            task_data = self.queue.pull(timeout=1)
            
            if task_data:
                print(f"📦 Processing task {task_data['id']}")
                try:
                    self.queue.execute_task(task_data)
                    processed += 1
                    print(f"✅ Task {task_data['id']} completed")
                except Exception as e:
                    print(f"❌ Task {task_data['id']} failed: {e}")
        
        print(f"🛑 Worker {self.worker_id} stopped.  Processed {processed} tasks")
    
    def stop(self):
        """Stop worker"""
        self.running = False


# Example usage
if __name__ == "__main__":
    # Initialize queue
    queue = RedisTaskQueue(queue_name='my_tasks')
    
    # Define tasks
    def slow_task(n:  int) -> int:
        import time
        time.sleep(2)
        return n * 2
    
    # Producer:  Push tasks
    task_ids = []
    for i in range(5):
        task_id = queue.push(slow_task, i, priority=i)
        task_ids.append(task_id)
        print(f"✅ Pushed task {task_id} with priority {i}")
    
    print(f"📊 Queue size: {queue.size()}")
    
    # Consumer: Process tasks
    worker = TaskWorker(queue, worker_id='worker-1')
    worker.start(max_tasks=5)
    
    # Get results
    for task_id in task_ids: 
        result = queue.get_result(task_id)
        print(f"📋 Task {task_id} result: {result}")