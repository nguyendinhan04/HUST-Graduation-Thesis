from contextlib import asynccontextmanager
import logging

from outbox_dispatcher import OutboxDispatcher

try:
	from job_matcher_app.outbox import ensure_task_outbox_table
except ImportError:
	from outbox import ensure_task_outbox_table  # type: ignore


@asynccontextmanager
async def lifespan(app):
	logging.info("Starting FastAPI app.")
	logging.info("ML embeddings are handled by the skill worker container.")
	ensure_task_outbox_table()

	outbox_dispatcher = OutboxDispatcher()
	outbox_dispatcher.start()

	try:
		yield
	finally:
		await outbox_dispatcher.stop()

	logging.info("Shutting down FastAPI app.")
