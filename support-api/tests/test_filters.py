from support_api.filters import filter_by_priority, filter_by_tenant

def test_filter_by_priority_urgent_subset(seed_tickets):
    urgent = filter_by_priority(seed_tickets, "urgent")
    assert all(ticket["priority"] == "urgent" for ticket in urgent)

def test_filter_by_tenant_scopes_correctly(seed_tickets):
    acme = filter_by_tenant(seed_tickets, "acme-corp")
    assert all(ticket["tenant"] == "acme-corp" for ticket in acme)