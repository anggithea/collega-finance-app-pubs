import os
import streamlit as st
from dotenv import load_dotenv
from ui.sidebar import sidebar_section
from ui.chat_interface import render_chat_interface
from utils.memory import init_chat_history, create_new_session
from services.document_handler import handle_document_upload

# Load environment variables
load_dotenv()

# Check required API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SECTORS_API_KEY = os.getenv("SECTORS_API_KEY")


def main():
    # Page config
    st.set_page_config(
        page_title="Collega AI Chatbot",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Check API keys
    if not GROQ_API_KEY:
        st.error("❌ GROQ_API_KEY tidak ditemukan! Set di file .env")
        st.stop()

    if not SECTORS_API_KEY:
        st.warning("⚠️ SECTORS_API_KEY tidak ditemukan. Financial features akan dinonaktifkan.")

    # Sidebar
    sidebar_section()

    # Initialize chat session
    if "current_session" not in st.session_state:
        create_new_session()
    init_chat_history(st.session_state.get("current_session"))

    # Title
    st.title("Collega AI Chatbot 🤖")
    st.caption("Powered by Llama 3.3 70B via Groq API with Financial Data Integration")

    # Handle document upload for RAG
    handle_document_upload()

    # Render chat interface
    render_chat_interface()


if __name__ == "__main__":
    main()