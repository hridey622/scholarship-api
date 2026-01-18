"""FastAPI main application entry point"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

from . import __version__
from .config import get_settings
from .routers import session_router, form_router
from .models import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("[*] Scholarship Form-Filling API starting...")
    settings = get_settings()
    print(f"    Ollama URL: {settings.ollama_url}")
    print(f"    Ollama Model: {settings.ollama_model}")
    print(f"    Form URL: {settings.form_url}")
    
    yield
    
    # Shutdown
    print("[*] Scholarship Form-Filling API shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Scholarship Form-Filling API",
    description="""
## Scholarship Form-Filling API

A production-ready API for processing voice/text input and filling scholarship eligibility forms.

### Features
- **Session Management**: Multi-step conversation with session tracking
- **Speech-to-Text**: Audio upload and transcription via Bhashini API
- **LLM Extraction**: Intelligent data extraction using Ollama/Llama
- **Form Automation**: Headless browser form filling with screenshots

### Workflow
1. Start a session with `POST /session/start`
2. Get current questions with `GET /session/{id}/questions`
3. Submit answers via `POST /session/{id}/text` or `POST /session/{id}/audio`
4. Preview data with `GET /form/{id}/preview`
5. Fill form with `POST /form/{id}/fill`
6. View screenshot with `GET /form/{id}/screenshot`

### Note
The scholarship website requires CAPTCHA completion which cannot be automated.
    """,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(session_router)
app.include_router(form_router)


@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "name": "Scholarship Form-Filling API",
        "version": __version__,
        "documentation": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    settings = get_settings()
    
    # Check Ollama
    ollama_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            if response.status_code == 200:
                ollama_status = "healthy"
            else:
                ollama_status = "unhealthy"
    except Exception:
        ollama_status = "unreachable"
    
    # Check Bhashini (just ping)
    bhashini_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.options(settings.bhashini_url)
            if response.status_code < 500:
                bhashini_status = "healthy"
            else:
                bhashini_status = "unhealthy"
    except Exception:
        bhashini_status = "unreachable"
    
    return HealthResponse(
        status="healthy" if ollama_status == "healthy" else "degraded",
        version=__version__,
        ollama_status=ollama_status,
        bhashini_status=bhashini_status
    )


@app.get("/stats", tags=["Admin"])
async def get_stats():
    """Get API statistics"""
    from .services import get_session_manager
    session_manager = get_session_manager()
    return session_manager.get_stats()
