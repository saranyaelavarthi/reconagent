"""
Generates three synthetic datasets that simulate a real reconciliation problem:
  1. settlement.csv     -> what Razorpay says was settled
  2. ledger.csv          -> what your internal system recorded
  3. bank_statement.csv  -> what actually hit the bank account

~18% of rows are deliberately broken (fees, timing, duplicates, rounding,
partial refunds, missing entries) so the matcher has real work to do.
"""
import pandas as pd
import random
from datetime import datetime, timedelta

random.seed(42)
N = 80  # total transactions -> comfortably clears the 50+ record bar

merchants = ["Zepto", "BlueDart Logistics", "Curefit", "Chaayos", "Lenskart",
             "Urban Company", "Nykaa", "Swiggy Instamart", "Meesho", "Boat Lifestyle"]

rows_settlement, rows_ledger, rows_bank = [], [], []
start_date = datetime(2026, 8, 1)

for i in range(N):
    txn_id = f"txn_{1000+i}"
    merchant = random.choice(merchants)
    amount = round(random.uniform(200, 15000), 2)
    fee = round(amount * 0.02, 2)
    net = round(amount - fee, 2)
    date = start_date + timedelta(days=random.randint(0, 20))

    scenario = random.random()

    # Base settlement row (always present)
    rows_settlement.append({"txn_id": txn_id, "merchant": merchant,
                             "gross_amount": amount, "fee": fee, "net_amount": net,
                             "settlement_date": date.strftime("%Y-%m-%d")})

    if scenario < 0.60:
        # Clean match: ledger and bank agree exactly
        rows_ledger.append({"txn_id": txn_id, "merchant": merchant,
                             "recorded_amount": net, "record_date": date.strftime("%Y-%m-%d")})
        rows_bank.append({"txn_id": txn_id, "credited_amount": net,
                           "value_date": date.strftime("%Y-%m-%d")})

    elif scenario < 0.72:
        # Timing gap: bank credit lands 2-4 days later
        rows_ledger.append({"txn_id": txn_id, "merchant": merchant,
                             "recorded_amount": net, "record_date": date.strftime("%Y-%m-%d")})
        late_date = date + timedelta(days=random.randint(2, 4))
        rows_bank.append({"txn_id": txn_id, "credited_amount": net,
                           "value_date": late_date.strftime("%Y-%m-%d")})

    elif scenario < 0.80:
        # Rounding / currency conversion drift (a few paise/rupees off)
        drift = round(random.uniform(0.5, 3.0), 2)
        rows_ledger.append({"txn_id": txn_id, "merchant": merchant,
                             "recorded_amount": net, "record_date": date.strftime("%Y-%m-%d")})
        rows_bank.append({"txn_id": txn_id, "credited_amount": round(net - drift, 2),
                           "value_date": date.strftime("%Y-%m-%d")})

    elif scenario < 0.87:
        # Partial refund: bank shows less than ledger
        refund = round(amount * random.uniform(0.1, 0.4), 2)
        rows_ledger.append({"txn_id": txn_id, "merchant": merchant,
                             "recorded_amount": net, "record_date": date.strftime("%Y-%m-%d")})
        rows_bank.append({"txn_id": txn_id, "credited_amount": round(net - refund, 2),
                           "value_date": date.strftime("%Y-%m-%d")})

    elif scenario < 0.93:
        # Duplicate bank entry (double credit — real ops nightmare)
        rows_ledger.append({"txn_id": txn_id, "merchant": merchant,
                             "recorded_amount": net, "record_date": date.strftime("%Y-%m-%d")})
        rows_bank.append({"txn_id": txn_id, "credited_amount": net,
                           "value_date": date.strftime("%Y-%m-%d")})
        rows_bank.append({"txn_id": txn_id + "_dup", "credited_amount": net,
                           "value_date": date.strftime("%Y-%m-%d")})

    else:
        # Missing entirely from bank (still pending / lost) — the honest exception
        rows_ledger.append({"txn_id": txn_id, "merchant": merchant,
                             "recorded_amount": net, "record_date": date.strftime("%Y-%m-%d")})
        # no bank row at all

pd.DataFrame(rows_settlement).to_csv("data/settlement.csv", index=False)
pd.DataFrame(rows_ledger).to_csv("data/ledger.csv", index=False)
pd.DataFrame(rows_bank).to_csv("data/bank_statement.csv", index=False)

print(f"Generated {N} settlement rows, {len(rows_ledger)} ledger rows, {len(rows_bank)} bank rows.")
print("Files written to data/settlement.csv, data/ledger.csv, data/bank_statement.csv")
