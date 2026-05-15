from fastapi import FastAPI

from lifespan import lifespan
from api.routes import recommendations_router, users_router


app = FastAPI(title="Job Recommendation App", lifespan=lifespan)
app.include_router(recommendations_router)
app.include_router(users_router)


@app.get("/health")
def health_check():
	return {"status": "ok"}
