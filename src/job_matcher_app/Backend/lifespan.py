from contextlib import asynccontextmanager
import logging


@asynccontextmanager
async def lifespan(app):
	logging.info("Starting FastAPI app.")
	logging.info("ML embeddings are handled by the skill worker container.")

	yield

	logging.info("Shutting down FastAPI app.")
