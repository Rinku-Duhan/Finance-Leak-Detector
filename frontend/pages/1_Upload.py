import streamlit as st

from api_client import require_login, upload_csv

st.set_page_config(page_title="Upload - Finance Leak Detector", page_icon="📤")
require_login()

st.title("📤 Upload a Statement")
st.write("Upload a bank/UPI transaction CSV. It'll be parsed, categorized, and scanned for leaks automatically.")

uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

if uploaded_file is not None:
    if st.button("Process this file"):
        with st.spinner("Parsing, categorizing, and running detectors..."):
            resp = upload_csv(uploaded_file.getvalue(), uploaded_file.name)

        if resp.status_code == 201:
            data = resp.json()
            st.success(f"Done! Status: **{data['status']}**")
            st.write(f"Upload ID: `{data['id']}`")
            st.info("Head to the Dashboard page to see the results.")
            st.session_state["last_upload_id"] = data["id"]
        else:
            try:
                detail = resp.json().get("detail", "Upload failed")
            except Exception:
                detail = resp.text
            st.error(f"Upload failed: {detail}")
