# app/main.py
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database import init_db
from app.routers import chat_mock, ingestion
import os

app = FastAPI(title="School Operations Agent Platform")

# Setup safe jinja templates path rendering hooks
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Automatically build local database schema tables on boot
@app.on_event("startup")
def on_startup():
    init_db()

# Middleware tracking global correlation IDs for the 9:00 audit timeline demo
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

# Serve the End-to-End Application Dashboard UI on the core root URL (/)
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard_ui(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# Include endpoint routes
app.include_router(chat_mock.router, prefix="/api/v1/mock", tags=["Chat Simulator"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Data Ingestion"])
