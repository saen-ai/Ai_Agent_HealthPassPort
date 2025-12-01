from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import Database
from app.features.auth.router import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for FastAPI application."""
    # Startup
    print("🚀 Starting Health Passport API...")
    await Database.connect_db()
    print("✅ Application started successfully")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    await Database.close_db()
    print("✅ Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Health Passport Backend API",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Health Passport API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    }
