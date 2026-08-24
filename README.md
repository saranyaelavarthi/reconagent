# ReconAgent

**Track:** AI Finance Controller — Razorpay AI Buildathon 2026

An agent that reconciles three sources of truth — a Razorpay settlement report, an internal ledger, and a bank statement — and produces an **honest, auditable** reconciliation: a real match rate on the full batch, every exception classified by reason, and a full audit trail explaining *why* each transaction did or didn't match.

## The problem

Reconciliation is rarely one clean step. Settlements land, but timing gaps, rounding drift, partial refunds, duplicate credits, and missing entries all creep in — and today this is mostly done by hand. This agent closes that loop: detect, classify, explain, and report — without cherry-picking the easy cases.

## Results (this run)

```
Total transactions:   80
Clean matches:        50   (62.5%)
Exceptions:           30
  TIMING_GAP:         11   — amount correct, credited late
  PARTIAL_REFUND:      8   — bank credited less than expected
  DUPLICATE:            7   — bank shows two credits for one transaction
  MISSING:              3   — no bank entry found at all
  ROUNDING_DRIFT:       1   — small currency/rounding difference
```

This is the **full batch result**, not a curated sample — including the transactions the agent could *not* cleanly resolve, per the track's own bar: "One cherry-picked match proves nothing."

## Architecture

```
settlement.csv ─┐
ledger.csv      ├──▶  reconcile.py  ──▶  reconciliation_report.json (full audit trail)
bank_statement.csv ┘         │                    │
                              │                    └──▶ exceptions.csv
                    ┌─────────┴──────────┐
                    │  1. Exact match     │  txn_id + amount + date, rule-based
                    │  2. Fuzzy match     │  tolerance-based amount/date matching
                    │  3. LLM resolution  │  classifies + explains ambiguous cases
                    │     (with rule-based fallback if no API key)
                    └────────────────────┘
                              │
                    app.py (Streamlit dashboard)
```

**Why this design:** rules handle the ~80% of cases that are genuinely simple (fast, cheap, deterministic, fully explainable). The LLM is used only where it earns its keep — classifying and explaining the ambiguous ~20% in plain language. If no `ANTHROPIC_API_KEY` is set, a deterministic rule-based classifier takes over automatically, so the pipeline **never silently breaks**.

## Running it

```bash
pip install -r requirements.txt

# optional — enables LLM-assisted reasoning on ambiguous cases
export ANTHROPIC_API_KEY=your_key_here

python generate_data.py     # generates synthetic settlement/ledger/bank data
python reconcile.py         # runs the full reconciliation, prints summary
streamlit run app.py        # interactive dashboard with the full audit trail
```

## What broke during development (and how it was fixed)

Early versions matched purely on amount, which produced false positives — two unrelated transactions of the same value were flagged as a "match" if dates were close. Fixed by requiring **both** amount tolerance and date tolerance to pass before calling something clean, and routing anything that fails either check to the classification layer instead of silently accepting it. This is also why duplicate bank credits are checked *before* the fuzzy-match pass — otherwise a duplicate could mask itself as a clean match.

## What I'd add with more time

- Multi-currency support (right now the tolerance model assumes INR)
- A "promise-to-pay" style retry loop for the MISSING category
- Precision/recall tracking against a labeled ground-truth set, not just match rate
