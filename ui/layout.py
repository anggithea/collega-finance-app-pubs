import streamlit as st

def setup_page():
    st.set_page_config(page_title="Groq Chatbot", page_icon="🤖", layout="wide")
    st.markdown("""
        <style>
            body {
                background: linear-gradient(120deg, #d4fc79, #96e6a1);
                font-family: 'Segoe UI', sans-serif;
            }
            .stChatMessage {
                border-radius: 20px;
                padding: 15px;
                margin-bottom: 10px;
            }
            .user {
                text-align: right;
            }
            .bot {
                text-align: left;
            }
            .stTextInput>div>div>input {
                font-size: 16px;
                padding: 10px;
            }
        </style>
    """, unsafe_allow_html=True)
