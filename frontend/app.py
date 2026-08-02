import streamlit as st

from api_client import login, signup, is_logged_in

st.set_page_config(page_title="Finance Leak Detector", page_icon="💸")

st.title("💸 Finance Leak Detector")


def _extract_error(resp) -> str:
    """Safely pull an error message out of a response, even if it's not
    JSON -- e.g. a raw Render gateway error page during a cold start,
    which is a 'successful' HTTP response with a non-JSON body."""
    try:
        return resp.json().get("detail", f"Request failed (status {resp.status_code})")
    except Exception:
        return f"Request failed (status {resp.status_code}). If the server was asleep, please try again in a moment."


if is_logged_in():
    st.success(f"Logged in as **{st.session_state.get('user_email', 'you')}**")
    st.write("Use the sidebar to upload a statement, view your dashboard, or check your upload history.")

    if st.button("Log out"):
        st.session_state.clear()
        st.rerun()

else:
    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in")

        if submitted:
            resp = login(email, password)
            if resp.status_code == 200:
                data = resp.json()
                st.session_state["access_token"] = data["access_token"]
                st.session_state["refresh_token"] = data["refresh_token"]
                st.session_state["user_email"] = email
                st.success("Logged in!")
                st.rerun()
            else:
                st.error(_extract_error(resp))

    with tab_signup:
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_password")
            submitted_signup = st.form_submit_button("Sign up")

        if submitted_signup:
            resp = signup(new_email, new_password)
            if resp.status_code == 201:
                data = resp.json()
                st.session_state["access_token"] = data["access_token"]
                st.session_state["refresh_token"] = data["refresh_token"]
                st.session_state["user_email"] = new_email
                st.success("Account created and logged in!")
                st.rerun()
            else:
                st.error(_extract_error(resp))
