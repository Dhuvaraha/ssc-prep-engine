from fastapi import FastAPI

from app.routers import auth, content, exams, health, practice

app = FastAPI(
    title="SSC Prep Engine API",
    version="0.1.0",
    description="Backend for adaptive SSC preparation, practice, mocks, analytics and revision.",
)

app.include_router(health.router)
app.include_router(exams.router, prefix="/api/v1")
app.include_router(practice.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "SSC Prep Engine API", "status": "running"}
