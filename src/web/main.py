"""
FastAPI web dashboard for ArXiv Content Automation System
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path
from uuid import UUID
import logging

from src.web.api import papers, insights, tags, dashboard, chat
from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository

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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routers
app.include_router(papers.router, prefix="/api/papers", tags=["papers"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

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

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Chat interface page."""
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/reader", response_class=HTMLResponse)
async def reader_page(request: Request, paper_id: str = None):
    """Dedicated reader page with PDF viewer and chat interface."""
    try:
        await db_manager.initialize()
        repo = PaperRepository()
        
        # Get all papers for the selector
        papers = await repo.list_all()
        
        # If paper_id is provided, get that specific paper
        selected_paper = None
        if paper_id:
            try:
                paper_uuid = UUID(paper_id)
                selected_paper = await repo.get_by_id(paper_uuid)
            except ValueError:
                # Invalid UUID, ignore
                pass
        
        # If no paper selected, use the first available paper
        if not selected_paper and papers:
            selected_paper = papers[0]
        
        return templates.TemplateResponse("reader.html", {
            "request": request,
            "papers": papers,
            "selected_paper": selected_paper
        })
        
    except Exception as e:
        logging.error(f"Error loading reader page: {e}")
        return templates.TemplateResponse("reader.html", {
            "request": request,
            "papers": [],
            "selected_paper": None,
            "error": "Error loading papers"
        })

@app.get("/papers/{paper_id}/pdf-viewer", response_class=HTMLResponse)
async def pdf_viewer_page(request: Request, paper_id: str):
    """PDF viewer page for a paper."""
    try:
        # Validate paper_id format
        paper_uuid = UUID(paper_id)
        
        # Get paper details for the template
        await db_manager.initialize()
        repo = PaperRepository()
        paper = await repo.get_by_id(paper_uuid)
        
        if not paper:
            # Return 404 page or redirect
            return templates.TemplateResponse("paper_detail.html", {
                "request": request, 
                "paper_id": paper_id,
                "error": "Paper not found"
            })
        
        return templates.TemplateResponse("pdf_viewer.html", {
            "request": request, 
            "paper": paper
        })
        
    except ValueError:
        # Invalid UUID format
        return templates.TemplateResponse("paper_detail.html", {
            "request": request, 
            "paper_id": paper_id,
            "error": "Invalid paper ID"
        })
    except Exception as e:
        # Other errors
        return templates.TemplateResponse("paper_detail.html", {
            "request": request, 
            "paper_id": paper_id,
            "error": f"Error loading paper: {str(e)}"
        })

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Dashboard is running"}

if __name__ == "__main__":
    uvicorn.run("src.web.main:app", host="0.0.0.0", port=8000, reload=True) 