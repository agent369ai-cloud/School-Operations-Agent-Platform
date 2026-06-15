LEGAL = {
    "NOT_STARTED":  ["IN_PROGRESS", "BLOCKED", "SUBMITTED"],
    "IN_PROGRESS":  ["BLOCKED", "SUBMITTED"],
    "BLOCKED":      ["IN_PROGRESS", "SUBMITTED"],
    "SUBMITTED":    ["FEEDBACK_GIVEN"],
    "FEEDBACK_GIVEN": ["REVISION_REQUESTED", "COMPLETED"],
    "REVISION_REQUESTED": ["SUBMITTED"],
    "COMPLETED":    [],
}
def transition(submission, to_state, db, correlation_id, actor_id):
    if to_state not in LEGAL[submission.state]:
        raise HTTPException(409, f"Cannot move {submission.state} → {to_state}")
    submission.state = to_state
    db.add(AuditEvent(correlation_id=correlation_id, actor_id=actor_id,
                      event_type=f"SUBMISSION_{to_state}",
                      payload={"submission_id": submission.id}))
    db.commit()