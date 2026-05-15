from contextlib import asynccontextmanager
import logging

from core.ml_loader import create_model_loader


@asynccontextmanager
async def lifespan(app):
	logging.info("Starting FastAPI app and loading ML models...")

	loader = create_model_loader()
	app.state.model_loader = loader
	app.state.tfidf_model = None

	try:
		app.state.tfidf_model = loader.load_model_tfidf()
		logging.info("TF-IDF model loaded successfully.")
	except Exception as exc:
		logging.exception("Failed to load TF-IDF model: %s", exc)

	logging.info("BERT/MiniLM embeddings are handled by skill_worker.py.")

	yield

	logging.info("Shutting down FastAPI app.")
