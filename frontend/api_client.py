"""
Shared API client for the Streamlit frontend.
"""

import os

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# Generous timeout to survive Render free-tier cold starts (backend can
# take 30-60s to wake up from sleep on the first request).
REQUEST_TIMEOUT = 90


def get_auth_headers() -> dict:
    token = st.session_state.get("access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def is_logged_in() -> bool:
    return "access_token" in st.session_state


def require_login():
    if not is_logged_in():
        st.warning("Please log in first (go to the Login page in the sidebar).")
        st.stop()


def _post(url, **kwargs):
    try:
        return requests.post(url, timeout=REQUEST_TIMEOUT, **kwargs)
    except requests.exceptions.RequestException as e:
        st.error(
            "Could not reach the server -- it may be waking up from sleep "
            "(free-tier hosting). Please wait a few seconds and try again."
        )
        st.stop()


def _get(url, **kwargs):
    try:
        return requests.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
    except requests.exceptions.RequestException as e:
        st.error(
            "Could not reach the server -- it may be waking up from sleep "
            "(free-tier hosting). Please wait a few seconds and try again."
        )
        st.stop()


def signup(email: str, password: str):
    return _post(f"{API_BASE_URL}/auth/signup", json={"email": email, "password": password})


def login(email: str, password: str):
    return _post(f"{API_BASE_URL}/auth/login", json={"email": email, "password": password})


def upload_csv(file_bytes: bytes, filename: str):
    files = {"file": (filename, file_bytes, "text/csv")}
    return _post(f"{API_BASE_URL}/transactions/upload", files=files, headers=get_auth_headers())


def list_uploads():
    return _get(f"{API_BASE_URL}/uploads/", headers=get_auth_headers())


def get_summary(upload_id: str):
    return _get(f"{API_BASE_URL}/dashboard/summary", params={"upload_id": upload_id}, headers=get_auth_headers())


def get_anomalies(upload_id: str):
    return _get(f"{API_BASE_URL}/dashboard/anomalies", params={"upload_id": upload_id}, headers=get_auth_headers())


def get_narrative(upload_id: str):
    return _get(f"{API_BASE_URL}/dashboard/narrative", params={"upload_id": upload_id}, headers=get_auth_headers())


def list_transactions(upload_id: str, page: int = 1, page_size: int = 50):
    return _get(
        f"{API_BASE_URL}/transactions/",
        params={"upload_id": upload_id, "page": page, "page_size": page_size},
        headers=get_auth_headers(),
    )
