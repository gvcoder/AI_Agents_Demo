from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.routers import (
    p01_prompt_chaining,
    p02_routing,
    p03_parallelization,
    p04_orchestrator_workers,
    p05_evaluator_optimizer,
    p06_react,
    p07_plan_and_execute,
)

app = FastAPI(
    title="AI Agent Design Patterns Playground",
    description="Interactive testbed for 20 AI Agent Design Patterns across modern frameworks.",
    version="1.0.0"
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register pattern routers
app.include_router(p01_prompt_chaining.router, prefix="/api")
app.include_router(p02_routing.router, prefix="/api")
app.include_router(p03_parallelization.router, prefix="/api")
app.include_router(p04_orchestrator_workers.router, prefix="/api")
app.include_router(p05_evaluator_optimizer.router, prefix="/api")
app.include_router(p06_react.router, prefix="/api")
app.include_router(p07_plan_and_execute.router, prefix="/api")

@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "default_provider": settings.DEFAULT_PROVIDER,
        "available_keys": {
            "gemini": bool(settings.GEMINI_API_KEY),
            "openai": bool(settings.OPENAI_API_KEY),
            "anthropic": bool(settings.ANTHROPIC_API_KEY),
        }
    }

