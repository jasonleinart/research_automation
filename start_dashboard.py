#!/usr/bin/env python3
"""
Start the ArXiv Content Automation Dashboard
"""

import uvicorn
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    print("🚀 Starting ArXiv Content Automation Dashboard...")
    print("📊 API Documentation will be available at: http://localhost:8000/docs")
    print("🔍 Interactive API docs at: http://localhost:8000/redoc")
    print("🌐 Dashboard API at: http://localhost:8000/api")
    print("\nPress Ctrl+C to stop the server")
    
    uvicorn.run(
        "src.web.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 