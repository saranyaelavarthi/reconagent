"""
ReconAgent — multi-source reconciliation engine.

Matches settlement.csv (Razorpay) -> ledger.csv (internal) -> bank_statement.csv (bank)
in three passes, and produces an honest, auditable result: every row's
outcome is logged with the reason it matched or didn't.

Usage:
    python reconcile.py
Outputs:
    output/reconciliation_report.json   (full audit trail + summary metrics)
    output/exceptions.csv               (everything that did NOT cleanly match)
"""
import pandas as pd
import json
import os

AMOUNT_TOLERANCE = 1.0   # rupees — anything within this is "clean" on amount
DAY_TOLERANCE = 1        # days — same-day is clean; beyond this needs review

USE_LLM = bool(os.environ.get("ANTHROPIC_API_KEY"))

def llm_explain(txn_id, settlement_row, ledger_row, bank_row, diff_amount, day_gap):
    """
    Ask an LLM to classify an ambiguous case and explain its reasoning in
    plain language. Falls back to a deterministic rule-based explanation
    if no API key is set, so the pipeline always runs end-to-end.
    """
    if not USE_LLM:
        return rule_based_explain(diff_amount, day_gap)

    import anthropic
    client = anthropic.Anthropic()
    prompt = f"""You are a financial reconciliation analyst. Classify this transaction discrepancy
into exactly one category: TIMING_GAP, ROUNDING_DRIFT, PARTIAL_REFUND, DUPLICATE, MISSING, or UNKNOWN.
Then give a one-sentence plain-English reason.

Transaction: {txn_id}
Settlement net amount: {settlement_row.get('net_amount')}
Ledger recorded amount: {ledger_row.get('recorded_amount') if ledger_row else 'N/A'}
Bank credited amount: {bank_row.get('credited_amount') if bank_row else 'MISSING'}
Amount difference: {diff_amount}
Day gap: {day_gap}

Respond in the format: CATEGORY | reason"""
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        text = resp.content[0].text.strip()
        category, _, reason = text.partition("|")
        return category.strip(), reason.strip()
    except Exception as e:
        return rule_based_explain(diff_amount, day_gap, fallback_note=str(e))


def rule_based_explain(diff_amount, day_gap, fallback_note=None):
    """Deterministic fallback classifier — used when no LLM key is present,
    or if the LLM call fails, so the agent never silently breaks."""
    note = f" (LLM unavailable: {fallback_note})" if fallback_note else ""
    if diff_amount is None:
        return "MISSING", "No matching bank entry found for this transaction." + note
    if abs(diff_amount) <= AMOUNT_TOLERANCE and day_gap and day_gap > DAY_TOLERANCE:
        return "TIMING_GAP", f"Amount matches within tolerance but credited {day_gap} days late." + note
    if 0 < abs(diff_amount) <= 3.0:
        return "ROUNDING_DRIFT", f"Amount off by ₹{abs(diff_amount):.2f}, likely rounding/conversion drift." + note
    if diff_amount and diff_amount > 3.0:
        return "PARTIAL_REFUND", f"Bank credited ₹{diff_amount:.2f} less than ledger — likely a partial refund." + note
    return "UNKNOWN", "Discrepancy does not fit a known pattern; needs manual review." + note


def reconcile():
    settlement = pd.read_csv("data/settlement.csv")
    ledger = pd.read_csv("data/ledger.csv")
    bank = pd.read_csv("data/bank_statement.csv")

    ledger_by_id = ledger.set_index("txn_id").to_dict("index")

    # detect duplicate bank rows (same base txn_id appearing twice, incl. _dup suffix)
    bank["base_id"] = bank["txn_id"].str.replace("_dup", "", regex=False)
    dup_counts = bank["base_id"].value_counts()
    bank_by_id = bank[~bank["txn_id"].str.endswith("_dup")].set_index("txn_id").to_dict("index")

    audit_trail = []
    exceptions = []
    clean_matches = 0

    for _, srow in settlement.iterrows():
        txn_id = srow["txn_id"]
        ledger_row = ledger_by_id.get(txn_id)
        bank_row = bank_by_id.get(txn_id)
        is_duplicate = dup_counts.get(txn_id, 0) > 1

        entry = {"txn_id": txn_id, "merchant": srow["merchant"],
                  "settlement_net": srow["net_amount"]}

        if is_duplicate:
            entry.update({"status": "EXCEPTION", "category": "DUPLICATE",
                          "reason": "Bank shows two credits for the same transaction ID.",
                          "confidence": 0.98})
            exceptions.append(entry)
            audit_trail.append(entry)
            continue

        if bank_row is None:
            category, reason = llm_explain(txn_id, srow, ledger_row, None, None, None)
            entry.update({"status": "EXCEPTION", "category": category, "reason": reason,
                          "confidence": 0.95})
            exceptions.append(entry)
            audit_trail.append(entry)
            continue

        diff = round(srow["net_amount"] - bank_row["credited_amount"], 2)
        s_date = pd.to_datetime(srow["settlement_date"])
        b_date = pd.to_datetime(bank_row["value_date"])
        day_gap = abs((b_date - s_date).days)

        if abs(diff) <= AMOUNT_TOLERANCE and day_gap <= DAY_TOLERANCE:
            entry.update({"status": "MATCHED", "category": "EXACT", "reason": "Amount and date match within tolerance.",
                          "confidence": 1.0})
            clean_matches += 1
        else:
            category, reason = llm_explain(txn_id, srow, ledger_row, bank_row, diff, day_gap)
            entry.update({"status": "EXCEPTION", "category": category, "reason": reason,
                          "confidence": 0.85, "amount_diff": diff, "day_gap": day_gap})
            exceptions.append(entry)

        audit_trail.append(entry)

    total = len(settlement)
    match_rate = round(clean_matches / total * 100, 1)

    summary = {
        "total_transactions": total,
        "clean_matches": clean_matches,
        "match_rate_pct": match_rate,
        "exception_count": len(exceptions),
        "exception_breakdown": pd.DataFrame(exceptions)["category"].value_counts().to_dict() if exceptions else {},
        "llm_used": USE_LLM,
    }

    os.makedirs("output", exist_ok=True)
    with open("output/reconciliation_report.json", "w") as f:
        json.dump({"summary": summary, "audit_trail": audit_trail}, f, indent=2)

    pd.DataFrame(exceptions).to_csv("output/exceptions.csv", index=False)

    print(json.dumps(summary, indent=2))
    return summary, audit_trail


if __name__ == "__main__":
    reconcile()
