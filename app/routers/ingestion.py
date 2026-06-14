from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.ai_parser import parse_assignment_brief
from app.services.scheduler import run_reminder_engine
from app.models import Assignment, AuditEvent, User
import uuid
import csv

router = APIRouter()

@router.post("/upload-brief")
async def upload_assignment_brief(
    request: Request,
    file: UploadFile = File(...), 
    classroom_id: str = "grade-7-a", 
    db: Session = Depends(get_db)
):
    contents = await file.read()
    document_text = contents.decode("utf-8")
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    
    parsed_data = parse_assignment_brief(document_text)
    
    audit_log = AuditEvent(
        correlation_id=correlation_id,
        actor_id="teacher-1",
        event_type="ASSIGNMENT_BRIEF_PARSED",
        payload={
            "filename": file.filename,
            "extracted_title": parsed_data.title,
            "is_ambiguous": parsed_data.is_ambiguous
        }
    )
    db.add(audit_log)
    
    if parsed_data.is_ambiguous:
        new_assignment = Assignment(
            id=str(uuid.uuid4()),
            classroom_id=classroom_id,
            title=parsed_data.title,
            instructions=parsed_data.instructions,
            due_date=None,
            status="DRAFT"
        )
        db.add(new_assignment)
        db.commit()
        
        return {
            "status": "REQUIRES_CLARIFICATION",
            "type": "ASSIGNMENT",
            "assignment_id": new_assignment.id,
            "correlation_id": correlation_id,
            "message": parsed_data.clarification_question,
            "extracted_draft": {
                "title": parsed_data.title,
                "subject": parsed_data.subject,
                "instructions": parsed_data.instructions
            }
        }
    
    new_assignment = Assignment(
        id=str(uuid.uuid4()),
        classroom_id=classroom_id,
        title=parsed_data.title,
        instructions=parsed_data.instructions,
        status="APPROVED"
    )
    db.add(new_assignment)
    db.commit()
    
    return {"status": "SUCCESSFULLY_CREATED", "assignment_id": new_assignment.id, "correlation_id": correlation_id}

@router.post("/upload-roster")
async def upload_roster_csv(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Parses a student roster CSV file. Detects duplicates or rows missing 
    guardian text and drops them into an unapproved review canvas layout.
    """
    contents = await file.read()
    decoded = contents.decode("utf-8").splitlines()
    reader = csv.DictReader(decoded)
    
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    errors = []
    processed_rows = []
    seen_names = set()
    
    for idx, row in enumerate(reader, start=1):
        name = row.get("name", "").strip()
        email = row.get("email", "").strip()
        guardian = row.get("guardian", "").strip()
        
        # Scenario Check 1: Duplicate Identification
        if name in seen_names:
            errors.append({"row": idx, "field": "name", "issue": f"Duplicate student name detected: '{name}'"})
            continue
        seen_names.add(name)
        
        # Scenario Check 2: Missing Guardian Contact Boundary
        if not guardian:
            errors.append({"row": idx, "field": "guardian", "issue": f"Student '{name}' is missing a linked guardian contact info"})
            continue
            
        processed_rows.append({"name": name, "email": email, "role": "STUDENT"})

    # Trace parsing activity to the absolute log
    audit_log = AuditEvent(
        correlation_id=correlation_id,
        actor_id="admin-1",
        event_type="ROSTER_CSV_INGESTED",
        payload={"filename": file.filename, "total_rows_evaluated": idx, "anomalies_found": len(errors)}
    )
    db.add(audit_log)
    db.commit()

    if errors:
        return {
            "status": "REQUIRES_CLARIFICATION",
            "type": "ROSTER",
            "correlation_id": correlation_id,
            "message": "Roster ingestion halted. Ambiguous anomalies surfaced during parsing canvas validation.",
            "anomalies": errors
        }

    # If clean, commit records directly into active user tables
    for s in processed_rows:
        new_user = User(name=s["name"], email=s["email"], role=s["role"], school_id="lincoln-high-id")
        db.add(new_user)
    db.commit()
    
    return {"status": "SUCCESSFULLY_CREATED", "processed_records": len(processed_rows), "correlation_id": correlation_id}

@router.post("/trigger-scheduler")
async def trigger_scheduler_endpoint(request: Request, db: Session = Depends(get_db)):
    correlation_id = request.state.correlation_id
    result = run_reminder_engine(db, correlation_id)
    return result

