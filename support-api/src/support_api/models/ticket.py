from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from datetime import datetime

Priority = Literal["urgent", "high", "normal", "low"]
Status = Literal["open", "in_progress", "waiting_on_customer", "resolved", "closed"]
Category = Literal["billing", "technical", "account", "general"]
Channel = Literal["email", "chat", "phone", "portal"]

class Ticket(BaseModel):
    """A single customer support ticket."""

    model_config = ConfigDict(extra="forbid") # prevent any extra properties from being included in the declaration of this object

    id: str = Field(pattern=r"^TKT-\d{5}$") 
    title: str = Field(min_length=5, max_length=200)
    body: str = Field(min_length=1)
    priority: Priority
    status: Status
    category: Category
    tenant: str = Field(min_length=1, max_length=50)
    customer_id: str = Field(pattern=r"^CUS-\d{5}$")
    assignee: str | None = None
    channel: Channel
    tags: list[str] = Field(default_factory=list, max_length=10)
    created_at: datetime
    updated_at: datetime

if __name__ == "__main__":
    import json
    from pathlib import Path
    from pydantic import ValidationError
    from support_api.filters import load_tickets

    raw_ticket = load_tickets()[0]

    # Valid input returns a ticket instance
    ticket = Ticket.model_validate(raw_ticket)
    # print(f"Valid: id={ticket.id}   priority={ticket.priority}")
    # print(f"Type of priority field: {type(ticket.priority).__name__}")

    # model_dump serializes back to a dict
    dumped = ticket.model_dump()
    # print(f"Dumped keys: {sorted(dumped.keys())}")
    # print(f"Entire model dict: {dumped}")

    # Invalid input raising a structured error
    try:
        Ticket.model_validate({**raw_ticket, "priority": "blocker"}) # this a correct ticket in terms of keys, but priority is wrong
    except ValidationError as err:
        print("Validation error raised with:")
        for detail in err.errors():
            print(f"    loc={detail["loc"]}     type={detail["type"]}       msg={detail["msg"]}")