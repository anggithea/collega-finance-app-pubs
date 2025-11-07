import streamlit as st
from utils.memory import load_all_chat_sessions, create_new_session, init_chat_history

def sidebar_section():
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/4712/4712039.png", width=100)
    st.sidebar.title("Collega AI Chatbot 🤖")

    sessions = load_all_chat_sessions()
    session_names = list(sessions.keys())[::-1]  # tampilkan yang terbaru di atas

    # Tombol New Chat
    if st.sidebar.button("➕ New Chat", use_container_width=True):
        new_session = create_new_session()
        init_chat_history(new_session)
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("💬 Chat History")

    if not session_names:
        st.sidebar.info("Belum ada chat history.")
    else:
        for name in session_names:
            is_selected = (
                "current_session" in st.session_state
                and st.session_state.current_session == name
            )
            if st.sidebar.button(
                f"🗨️ {name}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                init_chat_history(name)
                st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.caption("Built using Llama 3.3 - Groq API")
