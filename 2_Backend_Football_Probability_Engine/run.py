"""
FastAPI Server Entry Point
Run this file to start the development server
"""
import uvicorn
from app.config import settings

if __name__ == "__main__":
    # Default values if not in settings
    host = getattr(settings, 'HOST', '0.0.0.0')
    port = getattr(settings, 'PORT', 8000)
    log_level = getattr(settings, 'LOG_LEVEL', 'INFO').lower()
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=["app"],
        log_level=log_level
    )

