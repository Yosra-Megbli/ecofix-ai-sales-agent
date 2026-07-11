"""FastAPI application for AI Sales Agent."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.config import CORS_ORIGINS
from backend.routes import leads, chat, dashboard

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
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# Mount static files for Chat UI
app.mount("/chat-ui", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/dashboard", tags=["dashboard"])
async def get_dashboard():
    """Serve dashboard HTML page."""
    return FileResponse("frontend/dashboard.html")

@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint."""
    return {"message": "AI Sales Agent API is running", "version": "0.1.0"}

# Root static files mount to serve assets for root-level routes
# (must stay LAST so /health, /dashboard, /chat-ui above take priority)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend_root")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)