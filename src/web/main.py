"""
FastAPI web dashboard for ArXiv Content Automation System
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
from pathlib import Path

from src.web.api import papers, insights, tags, dashboard

# Create FastAPI app
app = FastAPI(
    title="ArXiv Content Automation Dashboard",
    description="Web dashboard for exploring research papers, insights, and tags",
    version="1.0.0"
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates
templates = Jinja2Templates(directory="templates")

# Include API routers
app.include_router(papers.router, prefix="/api/papers", tags=["papers"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/papers", response_class=HTMLResponse)
async def papers_page(request: Request):
    """Papers listing page."""
    return templates.TemplateResponse("papers.html", {"request": request})

@app.get("/papers/{paper_id}", response_class=HTMLResponse)
async def paper_detail_page(request: Request, paper_id: str):
    """Individual paper detail page."""
    return templates.TemplateResponse("paper_detail.html", {"request": request, "paper_id": paper_id})

@app.get("/insights", response_class=HTMLResponse)
async def insights_page(request: Request):
    """Insights listing page."""
    return templates.TemplateResponse("insights.html", {"request": request})

@app.get("/tags", response_class=HTMLResponse)
async def tags_page(request: Request):
    """Tags listing page."""
    return templates.TemplateResponse("tags.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Dashboard is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 