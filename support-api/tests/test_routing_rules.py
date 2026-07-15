import pytest

from support_api.routing_rules import (
    DEFAULT_RULES,
    MalformedTicket,
    NoMatchingRule,
    RoutingDecision,
    RoutingError,
    TaggedTicketRouter,
    TicketRouter
)

@pytest.fixture
def router() -> TicketRouter:
    return TicketRouter(DEFAULT_RULES)

def _ticket(**overrides):
    base = dict(
        id="TKT-99999", priority="normal", category="general",
        status="open", tenant="acme-corp",
    )
    return base | overrides

def test_urgent_billing_goes_to_finance_lead(router):
    decision = router.route(_ticket(priority="urgent", category="billing"))
    assert isinstance(decision, RoutingDecision)
    assert decision.queue == "finance-lead"

def test_unknown_category_rasies_NoMatchingRule(router):
    with pytest.raises(NoMatchingRule):
        router.route(_ticket(category="unknown-category"))

@pytest.mark.parametrize(
    "category,expected_queue",
    [
        ("billing", "billing-team"),
        ("technical", "tier2-tech"),
        ("account", "account-team"),
        ("general", "support-triage"),
    ]
)
def test_category_defaults(router, category, expected_queue):
    decision = router.route(_ticket(category=category))
    assert decision.queue == expected_queue

def test_router_routes_every_seed_ticket(router, seed_tickets):
    for ticket in seed_tickets:
        decision = router.route(ticket)
        assert decision.queue

def test_tagged_router_override_fires_for_vip_tag():
    tagged = TaggedTicketRouter(DEFAULT_RULES)
    decision = tagged.route(_ticket(category="technical", tags=["vip-tenant"]))
    assert decision.queue == TaggedTicketRouter.VIP_QUEUE # vip-escalation
    assert decision.rule_name == "tag-vip-override"


def test_tagged_router_falls_through_to_super_class(router):
    tagged = TaggedTicketRouter(DEFAULT_RULES)
    decision = tagged.route(_ticket(category="technical", tags=[]))
    normal_routing_decision = router.route(_ticket(category="technical", tags=[]))
    assert decision.queue == "tier2-tech"
    assert normal_routing_decision.queue == "tier2-tech"

def test_missing_field_raises_malformed_ticket(router):
    with pytest.raises(MalformedTicket) as exec_info:
        router.route({"id": "TKT-bad"}) # no category
    assert exec_info.value.missing == {"category", "priority"}