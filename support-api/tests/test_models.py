import pytest
from pydantic import ValidationError

from support_api.models import Ticket

def test_every_seed_ticket_validates(seed_tickets): 
    """Catches drift if any hand-edits to the tickets seed break the ticket validation."""
    for raw_ticket in seed_tickets:
        Ticket.model_validate(raw_ticket)

def test_invalid_priority_rejected(seed_tickets):
    first = dict(seed_tickets[0], priority="blocker")
    with pytest.raises(ValidationError):
        Ticket.model_validate(first) # expecting this to fail, test passes