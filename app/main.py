from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import Database
from app.features.auth.router import router as auth_router
from app.features.files.router import router as files_router
from app.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for FastAPI application."""
    # Startup
    logger.info("Starting Health Passport API...")
    await Database.connect_db()
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await Database.close_db()
    logger.info("Application shutdown complete")


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
app.include_router(files_router, prefix=settings.API_V1_PREFIX)


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


@app.post("/test-email")
async def test_email(email: str):
    """Test email sending endpoint."""
    from app.core.email import send_otp_email
    
    try:
        result = await send_otp_email(email, "1234", "signup")
        if result:
            return {"success": True, "message": f"Test email sent to {email}. Check your inbox and spam folder."}
        else:
            return {"success": False, "message": "Failed to send email. Check server logs for details."}
    except Exception as e:
        logger.error(f"Test email error: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}
