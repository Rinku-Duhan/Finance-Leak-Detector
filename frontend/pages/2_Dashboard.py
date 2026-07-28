import pandas as pd
import streamlit as st

from api_client import get_anomalies, get_narrative, get_summary, list_uploads, require_login

st.set_page_config(page_title="Dashboard - Finance Leak Detector", page_icon="📊", layout="wide")
require_login()

st.title("📊 Dashboard")

uploads_resp = list_uploads()
if uploads_resp.status_code != 200:
    st.error("Could not load your uploads.")
    st.stop()

uploads = uploads_resp.json()
if not uploads:
    st.info("No uploads yet. Go to the Upload page to add a statement.")
    st.stop()

options = {f"{u['filename']} ({u['uploaded_at'][:10]}) - {u['id'][:8]}": u["id"] for u in uploads}

default_index = 0
last_id = st.session_state.get("last_upload_id")
if last_id:
    for i, upload_id in enumerate(options.values()):
        if upload_id == last_id:
            default_index = i
            break

selected_label = st.selectbox("Select an upload", list(options.keys()), index=default_index)
upload_id = options[selected_label]

summary_resp = get_summary(upload_id)
if summary_resp.status_code != 200:
    st.error("Could not load summary for this upload.")
    st.stop()

summary = summary_resp.json()

col1, col2, col3 = st.columns(3)
col1.metric("Total Transactions", summary["total_transactions"])
col2.metric("Total Income", f"₹{summary['total_income']:,.2f}")
col3.metric("Total Spent", f"₹{summary['total_spent']:,.2f}")

st.subheader("Spending by Category")
by_category = summary["by_category"]
spend_only = {k: abs(v) for k, v in by_category.items() if v < 0}
if spend_only:
    chart_df = pd.DataFrame(list(spend_only.items()), columns=["Category", "Amount"]).set_index("Category")
    st.bar_chart(chart_df)

st.subheader("🚩 Detected Leaks")
anomalies_resp = get_anomalies(upload_id)
if anomalies_resp.status_code == 200:
    anomalies = anomalies_resp.json()
    if not anomalies:
        st.success("No leaks detected in this upload.")
    else:
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        anomalies_sorted = sorted(anomalies, key=lambda a: severity_order.get(a["severity"], 3))

        for a in anomalies_sorted:
            severity_color = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}.get(a["severity"], "⚪")
            with st.expander(f"{severity_color} [{a['severity']}] {a['type'].replace('_', ' ').title()}"):
                st.write(a["reason"])
                st.json(a["evidence"])
else:
    st.error("Could not load anomalies for this upload.")

st.subheader("📝 Monthly Summary")
if st.button("Generate summary"):
    with st.spinner("Asking the AI for a plain-language summary..."):
        narrative_resp = get_narrative(upload_id)
    if narrative_resp.status_code == 200:
        st.text(narrative_resp.json()["narrative"])
    else:
        st.error("Could not generate a summary right now.")