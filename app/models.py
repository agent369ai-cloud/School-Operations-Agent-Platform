# app/models.py
import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class School(Base):
    __tablename__ = "schools"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)

class ClassRoom(Base):
    __tablename__ = "classrooms"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id = Column(String, ForeignKey("schools.id", ondelete="CASCADE"))
    name = Column(String, nullable=False) # e.g., "Grade 7-A"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id = Column(String, ForeignKey("schools.id", ondelete="CASCADE"))
    email = Column(String, unique=True, nullable=True)
    role = Column(String, nullable=False) # "ADMIN", "TEACHER", "STUDENT", "GUARDIAN"
    name = Column(String, nullable=False)

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    classroom_id = Column(String, ForeignKey("classrooms.id"))
    title = Column(String, nullable=False)
    instructions = Column(String)
    due_date = Column(DateTime, nullable=True) # Nullable for AI ambiguity workflow
    status = Column(String, default="DRAFT") # "DRAFT", "APPROVED"

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    correlation_id = Column(String, index=True, nullable=False)
    actor_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False) # e.g., "ROSTER_PARSED", "ACCESS_DENIED"
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
class Guardian(Base):
    __tablename__ = "guardians"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id = Column(String, ForeignKey("schools.id"))
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)

class GuardianStudentLink(Base):
    __tablename__ = "guardian_student_links"
    guardian_id = Column(String, ForeignKey("guardians.id"), primary_key=True)
    student_id = Column(String, ForeignKey("users.id"), primary_key=True)

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id = Column(String, ForeignKey("schools.id"))
    uploaded_by = Column(String, ForeignKey("users.id"))
    doc_type = Column(String)  # "ROSTER", "BRIEF", "POLICY", "SUBMISSION"
    filename = Column(String)
    storage_path = Column(String)
    parsed_json = Column(JSON, nullable=True)
    approval_state = Column(String, default="PENDING")  # PENDING, APPROVED, REJECTED

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assignment_id = Column(String, ForeignKey("assignments.id"))
    student_id = Column(String, ForeignKey("users.id"))
    state = Column(String, default="NOT_STARTED")
    # NOT_STARTED, IN_PROGRESS, BLOCKED, SUBMITTED, FEEDBACK_GIVEN, REVISION_REQUESTED, COMPLETED
    content = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, ForeignKey("submissions.id"))
    teacher_id = Column(String, ForeignKey("users.id"))
    text = Column(String)
    decision = Column(String)  # REVISION_REQUESTED, COMPLETED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Invitation(Base):
    __tablename__ = "invitations"
    token = Column(String, primary_key=True)
    school_id = Column(String, ForeignKey("schools.id"))
    classroom_id = Column(String, ForeignKey("classrooms.id"), nullable=True)
    role = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_by = Column(String, ForeignKey("users.id"))