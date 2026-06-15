@router.post("/telegram")
async def telegram_webhook(req: Request, db=Depends(get_db),
                           x_telegram_bot_api_secret_token: str = Header(None)):
    if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(401)
    update = await req.json()
    msg = update.get("message")
    if not msg: return {"ok": True}
    env = ChatEnvelope(channel="telegram", sender_id=str(msg["from"]["id"]),
                       sender_name=msg["from"].get("first_name","unknown"),
                       text=msg["text"], message_id=str(msg["message_id"]),
                       received_at=datetime.utcnow())
    # Idempotency: check audit log for (channel, message_id)
    existing = db.query(AuditEvent).filter(
        AuditEvent.payload["channel"].as_string() == "telegram",
        AuditEvent.payload["message_id"].as_string() == env.message_id
    ).first()
    if existing: return {"ok": True, "dedup": True}
    # Route through same intent logic as chat_mock
    return route_intent(env, db, req.state.correlation_id)
```
**Setup steps:**
1. `pip install python-telegram-bot==21.*` (or just use httpx — you only need to receive)
2. `@BotFather` → `/newbot` → save token in `.env`
3. After deploy: `curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://school-operations-agent-platform-9lxk.onrender.com/api/v1/webhooks/telegram&secret_token=<SECRET>"`

**Outcome:** Deliverable #2 satisfied. Demo video shows real Telegram chat → dashboard updates live.

---

#### A6 [P0] · Refactor `chat_mock.py` to use the envelope + add idempotency
**File:** `app/routers/chat_mock.py`
**Changes:**
- Extract intent-routing into `app/services/intent_router.py` (so both mock and real Telegram call it)
- Add idempotency check on `(channel, message_id)` before processing
- Stop hardcoding student status — actually update a `Submission` row (after A4)

---

#### A7 [P1] · Add `Guardian` router & digest endpoint
**File:** `app/routers/guardians.py` (NEW)
- `POST /api/v1/guardians/opt-in` (scoped invite token)
- `GET /api/v1/guardians/me/digest` — redacted projection only (counts, not raw submission text)

---

### LANE B — Documentation deliverables (low effort, high rubric)

#### B1 [P0] · Rewrite `README.md` with structure reviewers expect
**File:** `README.md` (replace)

Your current README is dense prose without quick-start clarity. New structure:
1. **One-liner + screenshot** (take one from your dashboard)
2. **Mermaid architecture diagram** (renders on GitHub):
```
```mermaid
   flowchart LR
     T[Telegram] --> WH[/Webhook/]
     UI[Dashboard] --> API[FastAPI]
     WH --> IR[Intent Router]
     API --> AUTH[Auth/JWT]
     IR --> SVC[Services]
     SVC --> DB[(SQLite/Postgres)]
     SVC --> SSE[SSE Stream]
     SSE --> UI
     SVC --> AUDIT[(Audit Log)]
```