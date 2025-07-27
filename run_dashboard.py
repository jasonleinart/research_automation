#!/usr/bin/env python3
"""
Run the dashboard server for testing.
"""

import uvicorn
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    uvicorn.run(
        "src.web.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=["src", "templates"]
    )