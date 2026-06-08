from __future__ import annotations

import asyncio
import logging
import os
import uuid
from contextlib import suppress
from typing import Any

from redis import Redis

try:
    from job_matcher_app.outbox import (
        fetch_retryable_task_outboxes,
        mark_task_outbox_failed,
        requeue_task_outbox,
    )
except ImportError:
    from outbox import (  # type: ignore
        fetch_retryable_task_outboxes,
        mark_task_outbox_failed,
        requeue_task_outbox,
    )


logger = logging.getLogger("uvicorn.error")


def _get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class OutboxDispatcher:
    def __init__(self) -> None:
        self.enabled = _get_bool_env("OUTBOX_DISPATCHER_ENABLED", True)
        self.interval_seconds = _get_int_env("OUTBOX_DISPATCH_INTERVAL_SECONDS", 30)
        self.batch_size = _get_int_env("OUTBOX_DISPATCH_BATCH_SIZE", 50)
        self.pending_grace_seconds = _get_int_env("OUTBOX_PENDING_GRACE_SECONDS", 60)
        self.stale_after_seconds = _get_int_env(
            "OUTBOX_STALE_ENQUEUED_AFTER_SECONDS",
            900,
        )
        self.lock_name = os.getenv("OUTBOX_DISPATCH_LOCK_NAME", "outbox:dispatcher:lock")
        self.lock_ttl_seconds = _get_int_env(
            "OUTBOX_DISPATCH_LOCK_TTL_SECONDS",
            max(30, self.interval_seconds * 2),
        )
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._redis = Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=_get_int_env("REDIS_PORT", 6379),
            db=_get_int_env("REDIS_DB", 0),
            password=os.getenv("REDIS_PASSWORD") or None,
        )

    def start(self) -> None:
        if not self.enabled:
            logger.info("Outbox dispatcher disabled.")
            return
        if self._task is not None:
            return

        self._task = asyncio.create_task(self._run(), name="outbox-dispatcher")
        logger.info(
            "Outbox dispatcher started: interval=%ss batch_size=%s stale_after=%ss",
            self.interval_seconds,
            self.batch_size,
            self.stale_after_seconds,
        )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is None:
            return

        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        logger.info("Outbox dispatcher stopped.")

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.to_thread(self._dispatch_once_sync)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Outbox dispatcher tick failed.")

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

    def _dispatch_once_sync(self) -> None:
        lock_token = str(uuid.uuid4())
        acquired = self._redis.set(
            self.lock_name,
            lock_token,
            nx=True,
            ex=self.lock_ttl_seconds,
        )
        if not acquired:
            return

        try:
            rows = fetch_retryable_task_outboxes(
                limit=self.batch_size,
                stale_after_seconds=self.stale_after_seconds,
                pending_grace_seconds=self.pending_grace_seconds,
            )
            for row in rows:
                self._requeue_one(row)
        finally:
            self._release_lock(lock_token)

    def _requeue_one(self, row: dict[str, Any]) -> None:
        outbox_id = int(row["id"])
        if self._has_active_rq_job(row):
            return

        try:
            job_id = requeue_task_outbox(row, self._redis)
        except Exception as exc:
            mark_task_outbox_failed(outbox_id, exc)
            logger.exception("Failed to requeue outbox task id=%s.", outbox_id)
            return

        logger.info("Requeued outbox task id=%s as rq_job_id=%s.", outbox_id, job_id)

    def _has_active_rq_job(self, row: dict[str, Any]) -> bool:
        rq_job_id = row.get("rq_job_id")
        if not rq_job_id:
            return False

        try:
            from rq.job import Job
            from rq.exceptions import NoSuchJobError

            job = Job.fetch(str(rq_job_id), connection=self._redis)
            status = job.get_status(refresh=True)
        except NoSuchJobError:
            return False
        except Exception:
            logger.exception(
                "Failed to inspect RQ job %s for outbox task id=%s.",
                rq_job_id,
                row.get("id"),
            )
            return True

        status_value = getattr(status, "value", str(status)).lower()
        return status_value in {"queued", "started", "deferred", "scheduled"}

    def _release_lock(self, lock_token: str) -> None:
        release_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        end
        return 0
        """
        with suppress(Exception):
            self._redis.eval(release_script, 1, self.lock_name, lock_token)
