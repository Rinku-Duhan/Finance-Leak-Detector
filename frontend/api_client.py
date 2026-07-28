"""
Shared API client for the Streamlit frontend. Every page imports this
instead of calling `requests` directly, so the base URL and auth header
logic live in exactly one place.
"""

import os

import requests
import streamlit as st

# Configurable so this works both in plain local dev (127.0.0.1) and inside
# Docker Compose, where the frontend container must reach the backend
# container by its service name ("backend"), not 127.0.0.1.
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def get_auth_headers() -> dict:
    token = st.session_state.get("access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def is_logged_in() -> bool:
    return "access_token" in st.session_state


def require_login():
    """Call at the top of any page that needs auth. Stops the page
    render entirely if the user isn't logged in."""
    if not is_logged_in():
        st.warning("Please log in first (go to the Login page in the sidebar).")
        st.stop()


def signup(email: str, password: str) -> requests.Response:
    return requests.post(f"{API_BASE_URL}/auth/signup", json={"email": email, "password": password})


def login(email: str, password: str) -> requests.Response:
    return requests.post(f"{API_BASE_URL}/auth/login", json={"email": email, "password": password})


def upload_csv(file_bytes: bytes, filename: str) -> requests.Response:
    files = {"file": (filename, file_bytes, "text/csv")}
    return requests.post(f"{API_BASE_URL}/transactions/upload", files=files, headers=get_auth_headers())


def list_uploads() -> requests.Response:
    return requests.get(f"{API_BASE_URL}/uploads/", headers=get_auth_headers())


def get_summary(upload_id: str) -> requests.Response:
    return requests.get(
        f"{API_BASE_URL}/dashboard/summary", params={"upload_id": upload_id}, headers=get_auth_headers()
    )


def get_anomalies(upload_id: str) -> requests.Response:
    return requests.get(
        f"{API_BASE_URL}/dashboard/anomalies", params={"upload_id": upload_id}, headers=get_auth_headers()
    )


def get_narrative(upload_id: str) -> requests.Response:
    return requests.get(
        f"{API_BASE_URL}/dashboard/narrative", params={"upload_id": upload_id}, headers=get_auth_headers()
    )


def list_transactions(upload_id: str, page: int = 1, page_size: int = 50) -> requests.Response:
    return requests.get(
        f"{API_BASE_URL}/transactions/",
        params={"upload_id": upload_id, "page": page, "page_size": page_size},
        headers=get_auth_headers(),
    )