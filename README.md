# ReconAgent

**Reconciliation demo · Python · pandas · Streamlit**

Match synthetic settlement records against bank credits, inspect exceptions, and explore the results in a dashboard.

[Portfolio](https://github.com/saranyaelavarthi/development) · [Quick start](#quick-start) · [How it works](#how-it-works) · [Scope](#scope-and-limitations)

## At a glance

| Capability | Current implementation |
| --- | --- |
| Reproducible data | Seeded generator creates settlement, ledger, and bank CSV files. |
| Matching | Transaction IDs, amount tolerance, and settlement-to-bank date gaps. |
| Exception reporting | Delays, missing credits, duplicate markers, rounding differences, and possible partial refunds. |
| Investigation | JSON audit report, exception CSV, filters, and expandable dashboard records. |
| Optional AI assistance | Anthropic API explanations for exceptions; the default demo runs without an API key. |

## Quick start

Use Python 3.10 or newer. Run commands from the repository root.

```bash
git clone https://github.com/saranyaelavarthi/reconagent.git
cd reconagent
python -m venv .venv
```

Activate the environment:

- macOS / Linux: `source .venv/bin/activate`
- Windows PowerShell: `.venv\Scripts\Activate.ps1`

Then run:

```bash
python -m pip install -r requirements.txt
python generate_data.py
python reconcile.py
python -m streamlit run app.py
```

Open the local URL printed by Streamlit. The generator creates the `data/` directory automatically; reconciliation writes its results to `output/`.

No API key is needed for this path. If `ANTHROPIC_API_KEY` is already set in your environment, remove it to use only the rule-based demo. Setting it enables calls to the Anthropic API for exception explanations. Use synthetic data when exploring this option.

## How it works

1. **Generate:** create synthetic settlement, ledger, and bank records with a fixed random seed.
2. **Match:** look up bank records by transaction ID and compare credited amounts and dates against settlements.
3. **Classify:** report duplicate markers, missing credits, timing gaps, and amount differences.
4. **Inspect:** open the dashboard or read the exported audit and exception files.

The current clean-match tolerance is **₹1** and **one day**. Ledger records are loaded as context; the deterministic clean-match decision compares settlement and bank data.

## Reproduced demo result

The no-key pipeline was run on September 15, 2026 with the seeded dataset:

| Metric | Result |
| --- | ---: |
| Settlement transactions | 80 |
| Clean matches | 50 |
| Exceptions | 30 |
| Match rate for this dataset | 62.5% |

Exceptions: 11 timing gaps, 8 possible partial refunds, 7 duplicate cases, 3 missing credits, and 1 rounding difference. This is a synthetic demo result, not a production accuracy or performance benchmark.

## Repository guide

| File | Purpose |
| --- | --- |
| [generate_data.py](generate_data.py) | Creates the seeded CSV inputs. |
| [reconcile.py](reconcile.py) | Matches records, classifies exceptions, and exports reports. |
| [app.py](app.py) | Streamlit dashboard for reviewing results. |
| [requirements.txt](requirements.txt) | Python dependencies. |

Generated files: `data/settlement.csv`, `data/ledger.csv`, `data/bank_statement.csv`, `output/reconciliation_report.json`, and `output/exceptions.csv`.

## Scope and limitations

This is a learning prototype using synthetic CSVs. It has no live banking or Razorpay integration. Duplicate detection follows the generator's `_dup` convention; refund labels are heuristic explanations. Reported confidence values are illustrative and are not calibrated probabilities.

Full three-way ledger validation, production access controls, durable audit storage, and a regression test suite are future work.

## Next steps

- [ ] Validate the ledger independently of settlement-to-bank matching.
- [ ] Test malformed inputs, duplicate IDs, and empty datasets.
- [ ] Replace synthetic duplicate markers with explicit business keys.
- [ ] Add repeatable automated checks for classification rules.
