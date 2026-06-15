import uuid
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database import init_db, SessionLocal  # 1. Make sure to import your DB session factory
from app.repositories.school import SchoolRepository  # 2. Import your SchoolRepository class
from app.routers import chat_mock, ingestion, auth

app = FastAPI(title="School Operations Agent Platform")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

if not os.path.exists(TEMPLATES_DIR):
    TEMPLATES_DIR = os.path.join(os.getcwd(), "app", "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.on_event("startup")
def on_startup():
    init_db()

# --- REPOSITORY & STATE INJECTION MIDDLEWARE ---
@app.middleware("http")
async def attach_repositories_and_db(request: Request, call_next):
    # 3. Create a clean database session for this specific request
    db = SessionLocal()
    try:
        # 4. Bind the session to the repository and store it in request.state
        request.state.school_repository = SchoolRepository(db)
        
        # If your auth.py relies on string indexing (e.g., request.state["school_repository"]), 
        # add a fallback dictionary or keep it uniform:
        # request.state._state["school_repository"] = SchoolRepository(db)

        response = await call_next(request)
        return response
    finally:
        # 5. Always close the database connection when the request finishes
        db.close()

# --- CORRELATION ID MIDDLEWARE ---
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
    try:
        return templates.TemplateResponse("dashboard.html", {"request": request})
    except Exception as e:
        return f"<h1>Lincoln High School Dashboard Ready</h1><p>API logs are active. Please check <a href='/docs'>/docs</a> panel. System status: Healthy.</p><p style='color:red;'>Template Alert: {str(e)}</p>"

app.include_router(chat_mock.router, prefix="/api/v1/mock", tags=["Chat Simulator"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Data Ingestion"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Security Isolation Gateway"])
