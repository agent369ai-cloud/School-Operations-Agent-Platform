# app/main.py
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database import init_db
from app.routers import chat_mock, ingestion
import os

app = FastAPI(title="School Operations Agent Platform")

# 1. ⚠️ పాత్ ఇష్యూస్ రాకుండా ఇక్కడ లొకేషన్‌ను డైనమిక్‌గా కరెక్ట్ చేస్తున్నాం
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# ఒకవేళ రెండర్ సర్వర్ లో పాత్ కన్ఫ్యూజ్ అయితే బ్యాకప్ చెక్
if not os.path.exists(TEMPLATES_DIR):
    TEMPLATES_DIR = os.path.join(os.getcwd(), "app", "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.on_event("startup")
def on_startup():
    init_db()

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
    # ఒకవేళ ఏదైనా కారణం చేత టెంప్లేట్ ఫైల్ మిస్ అయితే క్రాష్ అవ్వకుండా ట్రై/ఎక్సెప్ట్ సేఫ్టీ గార్డ్
    try:
        return templates.TemplateResponse("dashboard.html", {"request": request})
    except Exception as e:
        # బ్యాకప్ ప్లాన్: ఒకవేళ HTML లోడ్ అవ్వకపోతే డెమో ఆగకుండా డైరెక్ట్ గా ఒక మెసేజ్ చూపిస్తుంది
        return f"<h1>Lincoln High School Dashboard Ready</h1><p>API logs are active. Please check <a href='/docs'>/docs</a> panel. System status: Healthy.</p><p style='color:red;'>Template Alert: {str(e)}</p>"

app.include_router(chat_mock.router, prefix="/api/v1/mock", tags=["Chat Simulator"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Data Ingestion"])
