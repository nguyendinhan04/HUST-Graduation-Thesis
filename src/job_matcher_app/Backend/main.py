from fastapi import FastAPI

from lifespan import lifespan
from api.routes import jobs_router, recommendations_router, users_router, auth_router


app = FastAPI(title="Job Recommendation App", lifespan=lifespan)
app.include_router(jobs_router)
app.include_router(recommendations_router)
app.include_router(users_router)
app.include_router(auth_router)


@app.get("/health")
def health_check():
	return {"status": "ok"}
