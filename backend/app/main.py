from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, engine
from app.routers import auth, content, exams, health, practice


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="SSC Prep Engine API",
    version="0.1.0",
    description="Backend for adaptive SSC preparation, practice, mocks, analytics and revision.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(exams.router, prefix="/api/v1")
app.include_router(practice.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "SSC Prep Engine API", "status": "running"}
