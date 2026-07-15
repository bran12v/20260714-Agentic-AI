# Day 03 Lab — Generators, Streaming, and Memory

## Objective

Yesterday's lecture introduced generators as the lazy alternative to lists. Today's lab makes the difference visible: you'll convert a list-based pipeline to a generator-based one and **measure** the memory footprint of each. Then you'll write a `chunk()` generator — a building block you'll reach for again every time you batch API calls or DB inserts in later weeks.

## Exercise 1: Convert a List Pipeline to a Generator Pipeline (~40 min)

**Goal:** Implement two versions of "count P1/P2 incidents older than 12 hours" — one with intermediate lists, one with generator pipelines — and measure the peak memory of each with `tracemalloc`.

**Estimated time:** 40 minutes.

1. Create `generator_pipeline.py` in your working directory.

2. Load incidents and pin `NOW = datetime(2026, 4, 28, tzinfo=timezone.utc)` for deterministic output.

3. Implement **Version A** — the list pipeline:

   ```python
   def count_via_lists(incidents: list[dict]) -> int:
       high_sev = [i for i in incidents if i["severity"] in {"P1", "P2"}]
       stale = [
           i for i in high_sev
           if (NOW - datetime.fromisoformat(i["opened_at"].replace("Z", "+00:00"))).total_seconds() / 3600 > 12
       ]
       return len(stale)
   ```

4. Implement **Version B** — generator helpers + a generator pipeline:

   ```python
   def _filter_high_sev(incidents):
       for i in incidents:
           if i["severity"] in {"P1", "P2"}:
               yield i

   def _filter_stale(incidents):
       for i in incidents:
           opened = datetime.fromisoformat(i["opened_at"].replace("Z", "+00:00"))
           if (NOW - opened).total_seconds() / 3600 > 12:
               yield i

   def count_via_generators(incidents) -> int:
       return sum(1 for _ in _filter_stale(_filter_high_sev(incidents)))
   ```

5. Wrap each function call with `tracemalloc` to measure peak memory:

   ```python
   import tracemalloc

   def measure(label, fn, *args):
       tracemalloc.start()
       result = fn(*args)
       _, peak = tracemalloc.get_traced_memory()
       tracemalloc.stop()
       print(f"{label:30s} result={result:3d} peak={peak:>7,} bytes")
   ```

6. Run both and print the comparison.

**Expected output:** Both functions return the same count (around 14). Peak memory differs — the list version may even use **less** at this scale because generator frames carry overhead. Don't be surprised; the win shows at 10K+ records, not 30.

> **Aside — when the generator wins.** Memory matters when: (a) the corpus is too large to fit in RAM (millions of rows from a DB cursor), (b) the consumer can short-circuit (e.g., `next(stream)` to grab the first match), or (c) intermediate transformations would otherwise allocate huge lists. For our 30-record dataset, none of those apply, so you see flat-or-worse numbers. The lesson isn't "always use generators" — it's "know when materializing matters and pick deliberately."

---

## Exercise 2: A Reusable `chunk()` Generator (~40 min)

**Goal:** Write a `chunk(stream, size)` generator that batches an upstream iterable into N-sized lists. This is the workhorse pattern for batched API calls, bulk DB inserts, and rate-limited fan-out.

**Estimated time:** 40 minutes.

1. Add to a new file `chunk_demo.py`:

   ```python
   def chunk(stream, size):
       """Yield successive chunks of `size` items from `stream`.
       The final chunk may be shorter if `stream` length isn't a multiple of `size`.
       Raises ValueError if size <= 0.
       """
       ...
   ```

2. Implementation guidance:
   - Maintain an internal `batch: list = []`.
   - For each item from `stream`, append; if the batch hits `size`, yield and reset.
   - After the loop, yield the remaining `batch` if non-empty.
   - Validate `size > 0` up front.

3. Test against four scenarios:

   | Input | Expected output |
   |-------|-----------------|
   | `chunk([], 5)` | `[]` |
   | `chunk([1, 2], 5)` | `[[1, 2]]` |
   | `chunk(range(10), 3)` | `[[0,1,2], [3,4,5], [6,7,8], [9]]` |
   | `chunk(stream_incidents(), 8)` | 4 batches: 8, 8, 8, 6 |

4. Print the last column for each, showing your `chunk()` produces it.

5. Define `stream_incidents()` as a generator function (NOT a list) that yields one incident at a time from `incidents.json`. Make sure your `chunk()` handles it as a true stream — i.e., your code does NOT call `list()` on the input first.

**Expected output:** All four test scenarios produce the documented batches.

> **Aside — chunking as a building block.** Almost every batched-API integration you'll write reaches for chunking: many embedding APIs accept up to 16 strings per call; SQL `INSERT` performance jumps when you batch 100s instead of inserting one-by-one; webhook fan-out lets a downstream rate-limit ~10 requests per second. Chunking decouples the upstream stream's natural rate (one ticket at a time, one row at a time) from the downstream batch's preferred shape. Once written, you stop thinking about it — and that's exactly the goal of a good utility.

---

## Stretch Goals

1. **`take(stream, n)` and `drop(stream, n)`.** Add two helpers that mirror Haskell/Clojure: `take` yields the first n items; `drop` skips the first n and yields the rest. Useful when you only need a sample for debugging.

2. **Async chunk.** Write `async def achunk(async_stream, size)` for `async for` consumers. Test it against an `async def` generator that yields incidents with a 10ms sleep between each.

---

## Quick Command Reference

| Command | Description |
|---------|-------------|
| `python generator_pipeline.py` | Run the list-vs-generator measurement |
| `python chunk_demo.py` | Run the chunk demonstrations |
| `python -c "import tracemalloc; tracemalloc.start(); x = [i for i in range(10000)]; print(tracemalloc.get_traced_memory())"` | One-line tracemalloc test |
| `python -c "def gen(): yield from range(3)\nfor x in gen(): print(x)"` | Smoke-test generator syntax |
