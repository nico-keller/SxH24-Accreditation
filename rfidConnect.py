import requests
import streamlit as st


def send_get_request(ip, invite_id):
    if not ip:
        return None
    
    full_url = f"http://{ip}:8080/getAttendee?attendeeId={invite_id}"
    try:
        response = requests.get(full_url)
        return response
    except Exception as e:
        # Handle exceptions, such as network errors
        st.error(f"Error sending GET request: {e}")
        return None