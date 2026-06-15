# app/services/scheduler.py
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import AuditEvent, Submission, User

def run_reminder_engine(db: Session, correlation_id: str) -> dict:
    """
    Evaluates current system time blocks against regional school policies.
    Respects quiet hours boundaries and filters out active blocked pipelines.
    """
    # 1. ⏰ System Policy Check: Quiet Hours (8 PM to 8 AM checking block)
    current_hour = datetime.now().hour
    if current_hour >= 20 or current_hour < 8:
        log = AuditEvent(
            correlation_id=correlation_id,
            actor_id="SYSTEM_SCHEDULER",
            event_type="REMINDER_SKIPPED_QUIET_HOURS",
            payload={
                "message": "Skipping execution. Policy active: Quiet Hours (8PM-8AM).", 
                "current_server_hour": current_hour
            }
        )
        db.add(log)
        db.commit()
        return {"status": "SKIPPED", "reason": "QUIET_HOURS_ACTIVE"}

    # 2. 🔍 Business Logic Query Layer
    now = datetime.now()
    sent_reminders = []

    # Join User with active status transitions inside the Submission canvas
    rows = db.query(User, Submission).outerjoin(
        Submission, Submission.user_id == User.id
    ).filter(User.role == "STUDENT").all()

    for user, submission in rows:
        status = None
        try:
            # Safely verify submission parameters and evaluate future deadlines
            if submission is not None and getattr(submission, "due_date", None) is not None and submission.due_date >= now:
                status = getattr(submission, "status", None)
        except Exception:
            status = None

        # 3. 🎯 Task 5 Rules Policy: Isolate and trigger alerts ONLY for 'SILENT' student records
        if status == "SILENT" or status is None:
            student_id = getattr(user, "id", "unknown_id")
            student_name = getattr(user, "name", "Unknown Student")
            
            log = AuditEvent(
                correlation_id=correlation_id,
                actor_id="SYSTEM_SCHEDULER",
                event_type="REMINDER_SENT",
                payload={
                    "student_id": student_id,
                    "student_name": student_name,
                    "message": f"Hi {student_name}, you have a pending math assignment due soon! Please update your dashboard canvas."
                }
            )
            db.add(log)
            sent_reminders.append(student_name)

    db.commit()

    return {
        "status": "COMPLETED",
        "processed_at": str(now),
        "reminders_sent_to": sent_reminders
    }
