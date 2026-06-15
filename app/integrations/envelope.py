from pydantic import BaseModel
from datetime import datetime
class ChatEnvelope(BaseModel):
    channel: str          # "telegram" | "whatsapp" | "mock"
    sender_id: str        # platform-specific id
    sender_name: str
    text: str
    message_id: str       # for idempotency
    received_at: datetime