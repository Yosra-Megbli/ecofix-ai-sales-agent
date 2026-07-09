"""FastAPI application for AI Sales Agent."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import CORS_ORIGINS
from backend.routes import leads

# Initialize FastAPI app
app = FastAPI(
    title="AI Sales Agent API",
    description="Backend API for AI Sales Agent - Lead Management",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leads.router, prefix="/leads", tags=["leads"])

@app.get("/", tags=["health"])
async def root():
    """Health check endpoint."""
    return {"message": "AI Sales Agent API is running", "version": "0.1.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
