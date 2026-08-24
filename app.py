"""
ReconAgent dashboard — run with: streamlit run app.py
Shows match rate, exception breakdown, and a click-to-expand audit trail
for every transaction the agent could not cleanly match.
"""
import streamlit as st
import pandas as pd
import json
import subprocess
import os

st.set_page_config(page_title="ReconAgent", layout="wide")
st.title("🔍 ReconAgent — Multi-Source Reconciliation")
st.caption("Razorpay settlement × internal ledger × bank statement, reconciled with a full audit trail.")

if not os.path.exists("output/reconciliation_report.json"):
    st.warning("No report found yet — generating data and running reconciliation now...")
    subprocess.run(["python", "generate_data.py"])
    subprocess.run(["python", "reconcile.py"])

with open("output/reconciliation_report.json") as f:
    report = json.load(f)

summary = report["summary"]
audit_trail = pd.DataFrame(report["audit_trail"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total transactions", summary["total_transactions"])
col2.metric("Match rate", f"{summary['match_rate_pct']}%")
col3.metric("Clean matches", summary["clean_matches"])
col4.metric("Exceptions", summary["exception_count"])

st.caption(f"LLM-assisted reasoning: {'enabled' if summary['llm_used'] else 'rule-based fallback (no API key set)'}")

st.subheader("Exception breakdown")
if summary["exception_breakdown"]:
    st.bar_chart(pd.Series(summary["exception_breakdown"]))
else:
    st.write("No exceptions — surprisingly clean batch.")

st.subheader("Full audit trail")
st.caption("Every transaction, matched or not, with the reason logged. Nothing here is cherry-picked.")

status_filter = st.multiselect("Filter by status", options=audit_trail["status"].unique().tolist(),
                                default=audit_trail["status"].unique().tolist())
filtered = audit_trail[audit_trail["status"].isin(status_filter)]

for _, row in filtered.iterrows():
    icon = "✅" if row["status"] == "MATCHED" else "⚠️"
    with st.expander(f"{icon} {row['txn_id']} — {row['merchant']} — {row['category']}"):
        st.write(f"**Status:** {row['status']}")
        st.write(f"**Reason:** {row['reason']}")
        st.write(f"**Confidence:** {row.get('confidence', 'N/A')}")
        if pd.notna(row.get("amount_diff")):
            st.write(f"**Amount difference:** ₹{row['amount_diff']}")
        if pd.notna(row.get("day_gap")):
            st.write(f"**Day gap:** {row['day_gap']} days")

st.divider()
st.caption("Built for the Razorpay AI Buildathon — AI Finance Controller track.")
