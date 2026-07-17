from typing import Any

import httpx
import structlog

_log = structlog.get_logger(__name__)

_DEFAULT_CONCURRENCY = 10

async def enrich_batch(
    tickets: list[dict[str, Any]],
    concurrency: int = _DEFAULT_CONCURRENCY,
    base_url: str = "https://httpbin.org",
) -> list[dict[str, Any]]:
    """Enrich many tickets concurrently (at the same time), 
    capped by a semaphore (concurrency limit)
    """
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=10.0) as client:

        async def _one(ticket: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                return await enrich_ticket(ticket, client, base_url=base_url)

        return await asyncio.gather(*(_one(ticket) for ticket in tickets)) # fan-out and join in one line (call)


async def enrich_ticket(
    ticket: dict[str, Any],
    client: httpx.AsyncClient,
    base_url: str = "https://httpbin.org",
) -> dict[str, Any]:
    """Fetch enrichment data for one ticket.
    
    Return a new dict - never mutates the existing input. The enrichment payload
    is whatever the mock endpoint echos back under 'args'
    """
    _log.info("enrichment_started", ticket_id=ticket["id"])
    response = await client.get(f"{base_url}/get", params={"customer_id": ticket["customer_id"]}) # https://httpbin.org/get
    """
    {
        "args": {
            "customer_id": "CUS-10001"
        },
        "headers": {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Host": "httpbin.org",
            "Postman-Token": "1186d112-cd87-4ecf-9f11-314295283bfa",
            "User-Agent": "PostmanRuntime/7.54.0",
            "X-Amzn-Trace-Id": "Root=1-6a5a3130-3c0442d8376d5c49687dd66e"
        },
        "origin": "162.224.168.219",
        "url": "https://httpbin.org/get?customer_id=CUS-10001"
    }
    """
    response.raise_for_status()
    echoed = response.json().get("args", {})
    _log.info("enrich_completed", ticket_id=ticket["id"], status=response.status_code)
    return { **ticket, "enrichment": echoed }

if __name__== "__main__":
    import asyncio
    import json
    from pathlib import Path

    from support_api.utils import atomic_write, timed
    from support_api.filters import load_tickets

    structlog.configure() # make our log statements go to STDOUT (console)

    async def main() -> None:
        tickets = load_tickets()[:20]
        try:
            results = await enrich_batch(tickets, concurrency=1)
        except httpx.RequestError as err:
            print(f"Network unreachable ({type(err).__name__}); skip this demo or retry later.")
            return
        print(f"\nEnriched {len(results)} tickets (concurrency=5)")
        print(f"First result enrichment: {results[0]["enrichment"]}")

        out = Path("enrich.json")
        with atomic_write(out) as fh:
            json.dump(results, fh, indent=2)
        print(f"Wrote: {out}")

    @timed(label="enrich-batch-run")
    def run() -> None: # timed is a synchronous function
        asyncio.run(main())

    run()


        # ticket = load_tickets()[0]
        # async with httpx.AsyncClient(timeout=10.0) as client:
        #     try:
        #         enriched = await enrich_ticket(ticket, client)
        #     except httpx.RequestError as err:
        #         print(f"Network unreachable ({type(err).__name__}); skip this demo or retry later.")
        #         return
        # print(f"{enriched["id"]} -> {enriched["enrichment"]}")

    # asyncio.run(main())