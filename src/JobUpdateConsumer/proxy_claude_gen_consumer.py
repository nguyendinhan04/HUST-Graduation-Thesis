from redis import Redis
from rq import Worker, Queue
from typing import List, Optional, Dict, Any
import signal
import sys
import logging
import json
import time
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages proxy retrieval and validation from Redis proxy pool"""

    def __init__(
        self,
        redis_conn: Redis,
        proxy_key: str = 'proxy_pool',
        max_retries: int = 3
    ):
        """
        Initialize proxy manager

        Args:
            redis_conn: Redis connection instance
            proxy_key: Key name for proxy pool in Redis
            max_retries: Maximum attempts to get a valid proxy
        """
        self.redis = redis_conn
        self.proxy_key = proxy_key
        self.max_retries = max_retries
        self.current_proxy = None

    def get_proxy(self) -> Optional[Dict[str, Any]]:
        """
        Get a proxy from the pool

        Returns:
            Proxy dict or None if no proxy available
        """
        try:
            # Get proxy from list (non-destructive peek)
            proxy_bytes = self.redis.lindex(self.proxy_key, 0)

            if proxy_bytes:
                proxy = json.loads(proxy_bytes)
                logger.info(f"✅ Retrieved proxy: {proxy.get('http', 'N/A')}")
                return proxy
            else:
                logger.warning("⚠️ No proxies available in pool")
                return None

        except Exception as e:
            logger.error(f"❌ Failed to get proxy: {e}")
            return None

    def pop_proxy(self) -> Optional[Dict[str, Any]]:
        """
        Pop a proxy from the pool (removes from list)

        Returns:
            Proxy dict or None if no proxy available
        """
        try:
            proxy_bytes = self.redis.lpop(self.proxy_key)

            if proxy_bytes:
                proxy = json.loads(proxy_bytes)
                logger.info(f"✅ Popped proxy: {proxy.get('http', 'N/A')}")
                self.current_proxy = proxy
                return proxy
            else:
                logger.warning("⚠️ No proxies available in pool")
                return None

        except Exception as e:
            logger.error(f"❌ Failed to pop proxy: {e}")
            return None

    def return_proxy(self, proxy: Dict[str, Any]):
        """
        Return a working proxy back to the pool

        Args:
            proxy: Proxy dict to return
        """
        try:
            self.redis.rpush(self.proxy_key, json.dumps(proxy))
            logger.info(f"✅ Returned proxy to pool: {proxy.get('http', 'N/A')}")
        except Exception as e:
            logger.error(f"❌ Failed to return proxy: {e}")

    def mark_proxy_failed(self, proxy: Dict[str, Any]):
        """
        Mark a proxy as failed (don't return to pool)

        Args:
            proxy: Proxy dict that failed
        """
        logger.warning(f"❌ Marking proxy as failed: {proxy.get('http', 'N/A')}")
        # Optionally store in failed list for later analysis
        try:
            failed_key = f"{self.proxy_key}:failed"
            self.redis.lpush(failed_key, json.dumps({
                **proxy,
                'failed_at': time.time()
            }))
        except Exception as e:
            logger.error(f"❌ Failed to mark proxy as failed: {e}")

    def get_proxy_count(self) -> int:
        """Get current count of proxies in pool"""
        try:
            return self.redis.llen(self.proxy_key)
        except Exception as e:
            logger.error(f"❌ Failed to get proxy count: {e}")
            return 0

    @contextmanager
    def use_proxy(self):
        """
        Context manager for using a proxy
        Automatically returns working proxy or marks as failed

        Usage:
            with proxy_manager.use_proxy() as proxy:
                if proxy:
                    # Use proxy for requests
                    pass
        """
        proxy = self.pop_proxy()
        success = False

        try:
            yield proxy
            success = True
        except Exception as e:
            logger.error(f"❌ Error while using proxy: {e}")
            success = False
            raise
        finally:
            if proxy:
                if success:
                    self.return_proxy(proxy)
                else:
                    self.mark_proxy_failed(proxy)


class ProxyAwareRedisConsumer:
    """
    Enhanced Redis Queue Consumer with Proxy Pool Integration

    Workflow:
    1. Consumer starts
    2. Before processing any task, it acquires a proxy from the pool
    3. If proxy acquired successfully, it processes tasks using that proxy
    4. After task completion, proxy is returned to pool (or marked as failed)
    5. Process repeats
    """

    def __init__(
        self,
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        queue_names: List[str] = None,
        proxy_key: str = 'proxy_pool',
        worker_name: Optional[str] = None,
        require_proxy: bool = True,  # If True, worker won't process without proxy
        proxy_rotation_interval: int = 10  # Rotate proxy every N jobs
    ):
        """
        Initialize proxy-aware consumer

        Args:
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database number
            redis_password: Redis password
            queue_names: List of queue names to consume from
            proxy_key: Key for proxy pool in Redis
            worker_name: Optional worker name
            require_proxy: If True, worker requires proxy to process tasks
            proxy_rotation_interval: Number of jobs before rotating proxy
        """
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

        # Proxy management
        self.proxy_manager = ProxyManager(
            redis_conn=self.redis_conn,
            proxy_key=proxy_key
        )

        self.worker_name = worker_name
        self.worker = None
        self.require_proxy = require_proxy
        self.proxy_rotation_interval = proxy_rotation_interval
        self.jobs_processed = 0
        self.current_proxy = None

    def _check_proxy_availability(self) -> bool:
        """Check if proxies are available before starting worker"""
        proxy_count = self.proxy_manager.get_proxy_count()
        logger.info(f"📊 Proxy pool status: {proxy_count} proxies available")

        if self.require_proxy and proxy_count == 0:
            logger.error("❌ No proxies available and require_proxy=True. Cannot start worker.")
            return False

        return True

    def _acquire_proxy(self) -> Optional[Dict[str, Any]]:
        """Acquire a proxy for processing tasks"""
        proxy = self.proxy_manager.pop_proxy()

        if proxy:
            self.current_proxy = proxy
            logger.info(f"✅ Acquired proxy for processing: {proxy.get('http', 'N/A')}")
            return proxy
        elif self.require_proxy:
            logger.error("❌ Failed to acquire proxy and require_proxy=True")
            return None
        else:
            logger.warning("⚠️ No proxy available but continuing without proxy")
            return None

    def _release_proxy(self, success: bool = True):
        """Release the current proxy"""
        if self.current_proxy:
            if success:
                self.proxy_manager.return_proxy(self.current_proxy)
            else:
                self.proxy_manager.mark_proxy_failed(self.current_proxy)

            self.current_proxy = None

    def _should_rotate_proxy(self) -> bool:
        """Check if proxy should be rotated"""
        return (self.proxy_rotation_interval > 0 and
                self.jobs_processed >= self.proxy_rotation_interval)

    def _custom_job_handler(self, job, queue):
        """Custom job handler that manages proxy lifecycle"""
        logger.info(f"🔄 Starting job {job.id} with proxy support")

        # Check if we need to rotate proxy
        if self._should_rotate_proxy():
            logger.info("🔄 Rotating proxy due to interval reached")
            self._release_proxy(success=True)
            self._acquire_proxy()
            self.jobs_processed = 0

        # Ensure we have a proxy if required
        if self.require_proxy and not self.current_proxy:
            self.current_proxy = self._acquire_proxy()
            if not self.current_proxy:
                logger.error(f"❌ Cannot process job {job.id} - no proxy available")
                raise Exception("No proxy available for processing")

        # Store proxy in job meta for task function access
        if self.current_proxy:
            job.meta['proxy'] = self.current_proxy
            job.save_meta()

        try:
            # Execute the job
            rv = job.perform()
            self.jobs_processed += 1
            logger.info(f"✅ Job {job.id} completed successfully (total: {self.jobs_processed})")
            return rv
        except Exception as e:
            logger.error(f"❌ Job {job.id} failed: {e}")
            # Mark proxy as potentially failed
            if self.current_proxy:
                logger.warning("⚠️ Job failed - may be due to proxy issue")
            raise

    def start_worker(
        self,
        burst: bool = False,
        max_jobs: Optional[int] = None
    ):
        """
        Start consuming tasks from queue with proxy support

        Args:
            burst: If True, process existing jobs and exit
            max_jobs: Maximum number of jobs to process before stopping
        """

        # Check proxy availability
        if not self._check_proxy_availability():
            logger.error("❌ Cannot start worker - proxy requirements not met")
            return

        # Acquire initial proxy
        if self.require_proxy or self.proxy_manager.get_proxy_count() > 0:
            self.current_proxy = self._acquire_proxy()
            if self.require_proxy and not self.current_proxy:
                logger.error("❌ Cannot start worker - failed to acquire initial proxy")
                return

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
            logger.info("🛑 Received shutdown signal, stopping worker...")
            self._release_proxy(success=True)
            if self.worker:
                self.worker.request_stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start worker
        logger.info(f"🚀 Starting proxy-aware worker for queues: {[q.name for q in self.queues]}")
        logger.info(f"   Proxy required: {self.require_proxy}")
        logger.info(f"   Proxy rotation interval: {self.proxy_rotation_interval} jobs")
        if self.current_proxy:
            logger.info(f"   Using proxy: {self.current_proxy.get('http', 'N/A')}")

        try:
            # Override job execution to inject proxy handling
            original_perform_job = self.worker.perform_job

            def proxy_aware_perform_job(job, queue):
                return self._custom_job_handler(job, queue)

            self.worker.perform_job = proxy_aware_perform_job

            # Start worker
            self.worker.work(
                burst=burst,
                max_jobs=max_jobs,
                with_scheduler=True
            )
        except Exception as e:
            logger.error(f"❌ Worker error: {e}")
            self._release_proxy(success=False)
            raise
        finally:
            # Clean up
            if self.current_proxy:
                self._release_proxy(success=True)

    def close(self):
        """Clean up connections"""
        if self.current_proxy:
            self._release_proxy(success=True)
        if self.redis_conn:
            self.redis_conn.close()


# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Proxy-Aware Redis Queue Worker')
    parser.add_argument('--queues', nargs='+', default=['default'],
                        help='Queue names to listen to')
    parser.add_argument('--burst', action='store_true',
                        help='Process existing jobs and exit')
    parser.add_argument('--worker-name', type=str, default=None,
                        help='Worker name')
    parser.add_argument('--proxy-key', type=str, default='proxy_pool',
                        help='Redis key for proxy pool')
    parser.add_argument('--require-proxy', action='store_true', default=True,
                        help='Require proxy to process tasks')
    parser.add_argument('--proxy-rotation', type=int, default=10,
                        help='Rotate proxy every N jobs (0=no rotation)')

    args = parser.parse_args()

    # Initialize consumer
    consumer = ProxyAwareRedisConsumer(
        redis_host='redis',
        redis_port=6379,
        queue_names=args.queues,
        proxy_key=args.proxy_key,
        worker_name=args.worker_name,
        require_proxy=args.require_proxy,
        proxy_rotation_interval=args.proxy_rotation
    )

    try:
        # Start worker (blocking call)
        consumer.start_worker(burst=args.burst)
    finally:
        consumer.close()





















# cach 2
from redis import Redis
from rq import Worker, Queue
from typing import List, Optional, Dict, Any
import signal
import sys
import logging
import json
import time
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages proxy retrieval and validation from Redis proxy pool"""

    def __init__(
        self,
        redis_conn: Redis,
        proxy_key: str = 'proxy_pool',
        max_retries: int = 3
    ):
        """
        Initialize proxy manager

        Args:
            redis_conn: Redis connection instance
            proxy_key: Key name for proxy pool in Redis
            max_retries: Maximum attempts to get a valid proxy
        """
        self.redis = redis_conn
        self.proxy_key = proxy_key
        self.max_retries = max_retries
        self.current_proxy = None

    def get_proxy(self) -> Optional[Dict[str, Any]]:
        """
        Get a proxy from the pool

        Returns:
            Proxy dict or None if no proxy available
        """
        try:
            # Get proxy from list (non-destructive peek)
            proxy_bytes = self.redis.lindex(self.proxy_key, 0)

            if proxy_bytes:
                proxy = json.loads(proxy_bytes)
                logger.info(f"✅ Retrieved proxy: {proxy.get('http', 'N/A')}")
                return proxy
            else:
                logger.warning("⚠️ No proxies available in pool")
                return None

        except Exception as e:
            logger.error(f"❌ Failed to get proxy: {e}")
            return None

    def pop_proxy(self) -> Optional[Dict[str, Any]]:
        """
        Pop a proxy from the pool (removes from list)

        Returns:
            Proxy dict or None if no proxy available
        """
        try:
            proxy_bytes = self.redis.lpop(self.proxy_key)

            if proxy_bytes:
                proxy = json.loads(proxy_bytes)
                logger.info(f"✅ Popped proxy: {proxy.get('http', 'N/A')}")
                self.current_proxy = proxy
                return proxy
            else:
                logger.warning("⚠️ No proxies available in pool")
                return None

        except Exception as e:
            logger.error(f"❌ Failed to pop proxy: {e}")
            return None

    def return_proxy(self, proxy: Dict[str, Any]):
        """
        Return a working proxy back to the pool

        Args:
            proxy: Proxy dict to return
        """
        try:
            self.redis.rpush(self.proxy_key, json.dumps(proxy))
            logger.info(f"✅ Returned proxy to pool: {proxy.get('http', 'N/A')}")
        except Exception as e:
            logger.error(f"❌ Failed to return proxy: {e}")

    def mark_proxy_failed(self, proxy: Dict[str, Any]):
        """
        Mark a proxy as failed (don't return to pool)

        Args:
            proxy: Proxy dict that failed
        """
        logger.warning(f"❌ Marking proxy as failed: {proxy.get('http', 'N/A')}")
        # Optionally store in failed list for later analysis
        try:
            failed_key = f"{self.proxy_key}:failed"
            self.redis.lpush(failed_key, json.dumps({
                **proxy,
                'failed_at': time.time()
            }))
        except Exception as e:
            logger.error(f"❌ Failed to mark proxy as failed: {e}")

    def get_proxy_count(self) -> int:
        """Get current count of proxies in pool"""
        try:
            return self.redis.llen(self.proxy_key)
        except Exception as e:
            logger.error(f"❌ Failed to get proxy count: {e}")
            return 0

    @contextmanager
    def use_proxy(self):
        """
        Context manager for using a proxy
        Automatically returns working proxy or marks as failed

        Usage:
            with proxy_manager.use_proxy() as proxy:
                if proxy:
                    # Use proxy for requests
                    pass
        """
        proxy = self.pop_proxy()
        success = False

        try:
            yield proxy
            success = True
        except Exception as e:
            logger.error(f"❌ Error while using proxy: {e}")
            success = False
            raise
        finally:
            if proxy:
                if success:
                    self.return_proxy(proxy)
                else:
                    self.mark_proxy_failed(proxy)


class ProxyAwareRedisConsumer:
    """
    Simplified Redis Queue Consumer with Proxy Pool Integration

    Workflow (Per Task):
    1. Ingest proxy from pool (wait if no proxy available)
    2. If proxy acquired → ingest task from queue
    3. Process task with proxy
    4. Return proxy to pool (or mark as failed)
    5. Repeat for next task
    """

    def __init__(
        self,
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        queue_names: List[str] = None,
        proxy_key: str = 'proxy_pool',
        worker_name: Optional[str] = None,
        proxy_wait_timeout: int = 60  # Wait up to N seconds for proxy
    ):
        """
        Initialize simplified proxy-aware consumer

        Args:
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database number
            redis_password: Redis password
            queue_names: List of queue names to consume from
            proxy_key: Key for proxy pool in Redis
            worker_name: Optional worker name
            proxy_wait_timeout: Seconds to wait for proxy (0 = wait forever)
        """
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

        # Proxy management
        self.proxy_manager = ProxyManager(
            redis_conn=self.redis_conn,
            proxy_key=proxy_key
        )

        self.worker_name = worker_name
        self.worker = None
        self.proxy_wait_timeout = proxy_wait_timeout
        self.jobs_processed = 0

    def _acquire_proxy_with_wait(self) -> Optional[Dict[str, Any]]:
        """
        Acquire a proxy from pool, wait if not available

        Returns:
            Proxy dict or None if timeout
        """
        start_time = time.time()
        wait_logged = False

        while True:
            # Try to get proxy
            proxy = self.proxy_manager.pop_proxy()

            if proxy:
                logger.info(f"✅ Acquired proxy: {proxy.get('http', 'N/A')}")
                return proxy

            # No proxy available
            if not wait_logged:
                logger.warning("⏳ No proxy available, waiting...")
                wait_logged = True

            # Check timeout
            if self.proxy_wait_timeout > 0:
                elapsed = time.time() - start_time
                if elapsed >= self.proxy_wait_timeout:
                    logger.error(f"❌ Timeout waiting for proxy ({self.proxy_wait_timeout}s)")
                    return None

            # Wait a bit before retry
            time.sleep(1)

    def _custom_job_handler(self, job, queue):
        """
        Custom job handler: Get fresh proxy for each task

        Workflow:
        1. Get proxy from pool (wait if needed)
        2. Process task with proxy
        3. Return proxy to pool
        """
        logger.info(f"🔄 Starting job {job.id}")

        # Step 1: Acquire proxy (wait if not available)
        proxy = self._acquire_proxy_with_wait()

        if not proxy:
            logger.error(f"❌ Cannot process job {job.id} - no proxy available")
            raise Exception("No proxy available for processing")

        # Step 2: Inject proxy into job metadata
        job.meta['proxy'] = proxy
        job.save_meta()

        # Step 3: Execute the job
        success = False
        try:
            logger.info(f"🚀 Processing job {job.id} with proxy {proxy.get('http', 'N/A')}")
            rv = job.perform()
            success = True
            self.jobs_processed += 1
            logger.info(f"✅ Job {job.id} completed successfully (total: {self.jobs_processed})")
            return rv
        except Exception as e:
            logger.error(f"❌ Job {job.id} failed: {e}")
            success = False
            raise
        finally:
            # Step 4: Always return or mark proxy
            if success:
                self.proxy_manager.return_proxy(proxy)
                logger.info(f"♻️ Returned proxy to pool")
            else:
                self.proxy_manager.mark_proxy_failed(proxy)
                logger.warning(f"🗑️ Marked proxy as failed")

    def start_worker(
        self,
        burst: bool = False,
        max_jobs: Optional[int] = None
    ):
        """
        Start consuming tasks from queue with proxy support

        Simplified workflow:
        - For each task, acquire fresh proxy → process → return proxy
        - Worker waits for proxy if not available

        Args:
            burst: If True, process existing jobs and exit
            max_jobs: Maximum number of jobs to process before stopping
        """

        # Check if proxy pool exists
        proxy_count = self.proxy_manager.get_proxy_count()
        logger.info(f"📊 Proxy pool status: {proxy_count} proxies available")

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
            logger.info("🛑 Received shutdown signal, stopping worker...")
            if self.worker:
                self.worker.request_stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start worker
        logger.info(f"🚀 Starting simplified proxy-aware worker")
        logger.info(f"   Queues: {[q.name for q in self.queues]}")
        logger.info(f"   Strategy: Fresh proxy per task")
        logger.info(f"   Proxy wait timeout: {self.proxy_wait_timeout}s (0=infinite)")

        try:
            # Override job execution to inject proxy handling
            def proxy_aware_perform_job(job, queue):
                return self._custom_job_handler(job, queue)

            self.worker.perform_job = proxy_aware_perform_job

            # Start worker
            self.worker.work(
                burst=burst,
                max_jobs=max_jobs,
                with_scheduler=True
            )
        except Exception as e:
            logger.error(f"❌ Worker error: {e}")
            raise

    def close(self):
        """Clean up connections"""
        if self.redis_conn:
            self.redis_conn.close()


# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Simplified Proxy-Aware Redis Queue Worker')
    parser.add_argument('--queues', nargs='+', default=['default'],
                        help='Queue names to listen to')
    parser.add_argument('--burst', action='store_true',
                        help='Process existing jobs and exit')
    parser.add_argument('--worker-name', type=str, default=None,
                        help='Worker name')
    parser.add_argument('--proxy-key', type=str, default='proxy_pool',
                        help='Redis key for proxy pool')
    parser.add_argument('--proxy-wait-timeout', type=int, default=60,
                        help='Seconds to wait for proxy (0=infinite)')

    args = parser.parse_args()

    # Initialize consumer
    consumer = ProxyAwareRedisConsumer(
        redis_host='redis',
        redis_port=6379,
        queue_names=args.queues,
        proxy_key=args.proxy_key,
        worker_name=args.worker_name,
        proxy_wait_timeout=args.proxy_wait_timeout
    )

    try:
        # Start worker (blocking call)
        consumer.start_worker(burst=args.burst)
    finally:
        consumer.close()



