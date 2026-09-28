from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.seed import seed_database
from app.api.auth import router as auth_router
from app.api.incidents import router as incidents_router
from app.api.am import router as am_router
from app.api.pm import router as pm_router
from app.api.matching import router as matching_router
from app.api.reconciliation import router as reconciliation_router
from app.api.evidence import router as evidence_router
from app.api.bob import router as bob_router
from app.api.reports import router as reports_router
from app.api.audit import router as audit_router
from app.api.evaluation import router as evaluation_router
from app.api.images import router as images_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="DVI-Bridge API",
    description="IBM Bob-Powered Disaster Victim Identification Coordination Platform with Gemini Cloud Multimodal Vision",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Safe Exception Handler (Never expose raw stack traces)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred during request processing. Details have been logged securely.",
            "path": request.url.path,
        },
    )


# Include API Routers
app.include_router(auth_router, prefix="/api")
app.include_router(incidents_router, prefix="/api")
app.include_router(am_router, prefix="/api")
app.include_router(pm_router, prefix="/api")
app.include_router(images_router, prefix="/api")
app.include_router(matching_router, prefix="/api")
app.include_router(reconciliation_router, prefix="/api")
app.include_router(evidence_router, prefix="/api")
app.include_router(bob_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(evaluation_router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "DVI-Bridge Backend",
        "version": settings.APP_VERSION,
        "bob_mode": "CONNECTED" if settings.BOB_API_KEY else "FALLBACK_OPERATIONAL",
        "gemini_vision_mode": "CONNECTED" if settings.GEMINI_API_KEY else "MOCK_OPERATIONAL",
        "gemini_model": settings.GEMINI_MODEL,
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
