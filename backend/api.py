from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import pathfinding

app = FastAPI(
    title="Mountain Path Finder API",
    description="Backend API for Mountain Path Finder",
    version="1.0.0",
)

# Configure CORS so the frontend can make requests to this backend
origins = [
    "http://localhost:5173", # Vue/Vite default port
    "http://127.0.0.1:5173",
    # Add your production frontend URL here later
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pathfinding.router)
from routers import settings
app.include_router(settings.router)

@app.get("/health", tags=["System"])
def health_check():
    """Basic health check endpoint"""
    return {"status": "ok", "message": "API is running"}

if __name__ == "__main__":
    import uvicorn
    # This allows you to run the API directly with `python api.py`
    uvicorn.run("api:app", host="0.0.0.1", port=8000, reload=True)
