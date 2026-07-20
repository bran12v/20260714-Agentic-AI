from flask import Blueprint, request

from support_api.filters import filter_by_priority, filter_by_tenant, load_tickets

# A blueprint is a group of routes that we attach to the app
bp = Blueprint("tickets", __name__)

@bp.route("", methods=["GET"]) # url endpoint, and HTTP verbs usable by this route # localhost:5000/
def list_tickets():
    """GET /tickets
        returns all tickets in the DB/JSON file.
    """
    # Gets all tickets
    tickets = load_tickets()

    # filters the total tickets down by priority
    priority = request.args.get("priority")
    if priority:
        tickets = filter_by_priority(tickets, priority)

    # filters the total tickets down by tenant
    tenant = request.args.get("tenant")
    if tenant:
        tickets = filter_by_tenant(tickets, tenant)
    
    return { "count": len(tickets), "items": tickets }

@bp.route("/<ticket_id>", methods=["GET"]) # /tickets/TKT-10001
def get_ticket(ticket_id: str):
    """GET /tickets/{id}
        returns an individual ticket based on the ID provided.
    """
    tickets = load_tickets()
    for ticket in tickets:
        if ticket["id"] == ticket_id:
            return ticket # 200 OK
    return { "error": "ticket_not_found", "ticket_id": ticket_id}, 404 # 404 not found