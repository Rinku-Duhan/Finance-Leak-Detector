import pandas as pd
import streamlit as st

from api_client import list_uploads, require_login

st.set_page_config(page_title="History - Finance Leak Detector", page_icon="🕓")
require_login()

st.title("🕓 Upload History")

resp = list_uploads()
if resp.status_code != 200:
    st.error("Could not load your upload history.")
    st.stop()

uploads = resp.json()

if not uploads:
    st.info("No uploads yet. Go to the Upload page to add your first statement.")
else:
    df = pd.DataFrame(uploads)
    df = df.rename(columns={
        "filename": "File",
        "uploaded_at": "Uploaded At",
        "status": "Status",
        "id": "Upload ID",
    })
    df = df[["File", "Uploaded At", "Status", "Upload ID"]]
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption("Go to the Dashboard page and select any of these uploads from the dropdown to view its results.")