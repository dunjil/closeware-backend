"""
Entry point for Railway and other platforms that look for main.py in root.
This simply imports and exposes the FastAPI app from app/main.py
"""
from app.main import app

# Expose the app for uvicorn
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
