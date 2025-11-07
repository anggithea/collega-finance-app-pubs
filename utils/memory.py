import json
import os
from datetime import datetime
import streamlit as st

HISTORY_FILE = "chat_history.json"


def load_all_chat_sessions():
    """Baca semua session chat dari file JSON."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except json.JSONDecodeError:
        return {}


def save_all_chat_sessions(sessions):
    """Simpan semua session chat ke file JSON."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)


def init_chat_history(session_id):
    """Inisialisasi chat history untuk session tertentu."""
    sessions = load_all_chat_sessions()
    st.session_state.current_session = session_id
    st.session_state.chat_history = sessions.get(session_id, [])


def save_current_session():
    """Simpan chat aktif tanpa menghapus session lain."""
    if "current_session" not in st.session_state:
        return

    # Load semua dulu agar tidak overwrite data lama
    sessions = load_all_chat_sessions()
    current = st.session_state.current_session
    sessions[current] = st.session_state.get("chat_history", [])
    save_all_chat_sessions(sessions)


def create_new_session():
    """Buat session baru dengan nama otomatis."""
    sessions = load_all_chat_sessions()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session_name = f"Session - {timestamp}"

    # Tambahkan session baru ke dict lama, jangan reset
    sessions[session_name] = []
    save_all_chat_sessions(sessions)

    # Set ke session state
    st.session_state.current_session = session_name
    st.session_state.chat_history = []

    return session_name
