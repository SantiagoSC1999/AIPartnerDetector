"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from src.api import institutions  # Will work when running from project root with backend path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="CLARISA Partners Duplicate Detection",
    description="Backend system for detecting duplicate institutions via Excel upload",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(institutions.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "CLARISA Partners Duplicate Detection Backend",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/api/version")
async def version():
    """Get API version."""
    return {"version": "1.0.0"}


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
