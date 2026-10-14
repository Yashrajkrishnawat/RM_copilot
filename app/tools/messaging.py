from typing import Literal

from pydantic import BaseModel, Field

from app.tools.registry import tool


class FollowupArgs(BaseModel):
    customer_name: str
    pending_docs: list[str]
    language: Literal["english", "hindi"] = "english"
    message: str = Field(description="The drafted WhatsApp message text")


@tool("draft_followup", "Save a drafted WhatsApp follow-up for RM approval. Does not send anything.",
      FollowupArgs, requires_approval=True)
def draft_followup(customer_name, pending_docs, language, message):
    return {"status": "pending_approval", "channel": "whatsapp", "to": customer_name,
            "language": language, "draft": message}