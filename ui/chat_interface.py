"""
UI Chat Interface untuk Streamlit dengan LangChain Agent Integration
"""
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from services.groq_service import get_chat_response
from services.rag_pipeline import retrieve_context
from services.agent_service import run_agent, is_financial_query, SECTORS_AVAILABLE
from utils.memory import save_current_session
from typing import Optional


def display_chat_history():
    """Menampilkan riwayat chat dari session state"""
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def convert_chat_history_to_langchain():
    """
    Konversi chat history dari format dict ke LangChain message objects

    Returns:
        list: List of LangChain message objects
    """
    langchain_history = []

    for message in st.session_state.chat_history:
        if message["role"] == "user":
            langchain_history.append(HumanMessage(content=message["content"]))
        elif message["role"] == "assistant":
            langchain_history.append(AIMessage(content=message["content"]))
        elif message["role"] == "system":
            langchain_history.append(SystemMessage(content=message["content"]))

    return langchain_history


def get_rag_context(prompt: str) -> tuple[str, list]:
    """
    Ambil context dari RAG jika ada vectorstore

    Args:
        prompt: User query

    Returns:
        tuple: (context_text, sources)
    """
    context_text = ""
    sources = []

    if "vectorstore" in st.session_state and st.session_state["vectorstore"] is not None:
        with st.spinner("📖 Mengambil konteks dari dokumen..."):
            context_text, sources = retrieve_context(st.session_state["vectorstore"], prompt)
            if context_text:
                st.info(f"📚 Ditemukan konteks dari dokumen: {len(sources)} sumber")

    return context_text, sources


def get_bot_response_with_agent(prompt: str, rag_context: str = "") -> Optional[str]:
    """
    Dapatkan response menggunakan LangChain Agent

    Args:
        prompt: User input
        rag_context: Context from RAG (optional)

    Returns:
        str: Bot response, or None if agent can't handle
    """
    chat_history = convert_chat_history_to_langchain()

    with st.spinner("🤖 Collega AI Agent sedang bekerja..."):
        try:
            response = run_agent(
                user_input=prompt,
                chat_history=chat_history,
                rag_context=rag_context
            )
            return response  # Could be None if agent can't handle
        except Exception as e:
            print(f"⚠️ Agent exception: {str(e)}")
            return None  # Return None to trigger fallback


def get_bot_response_standard(prompt: str, rag_context: str = "") -> str:
    """
    Dapatkan response menggunakan standard chat (tanpa agent)

    Args:
        prompt: User input
        rag_context: Context from RAG (optional)

    Returns:
        str: Bot response
    """
    # Build system prompt
    if rag_context:
        system_content = f"""You are Collega AI Assistant, a friendly and helpful chatbot.
Use the following context from uploaded documents to help answer:

Context:
{rag_context}

Always base your answer on the provided context when relevant."""
    else:
        system_content = "You are Collega AI Assistant, a friendly and helpful chatbot created to assist users."

    # Build messages
    messages = [{"role": "system", "content": system_content}]

    # Add chat history
    for msg in st.session_state.chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current prompt
    messages.append({"role": "user", "content": prompt})

    # Get response
    with st.spinner("🤖 Collega AI sedang menjawab..."):
        try:
            response = get_chat_response(messages)
            return response
        except Exception as e:
            return f"⚠️ Terjadi kesalahan: {str(e)}"


def handle_user_message(prompt: str):
    """
    Menangani input pesan dari user: simpan, proses, dan tampilkan response

    Args:
        prompt: Input pesan dari user
    """
    # Tambahkan pesan user ke chat history
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get RAG context jika ada
    rag_context, sources = get_rag_context(prompt)

    # Convert chat history to LangChain format for context
    langchain_history = convert_chat_history_to_langchain()

    # Deteksi jenis query dengan CONTEXT
    use_agent = is_financial_query(prompt, langchain_history) and SECTORS_AVAILABLE

    # ⬇️ TAMBAHKAN DEBUGGING INI
    print(f"=" * 50)
    print(f"USER INPUT: {prompt}")
    print(f"SECTORS_AVAILABLE: {SECTORS_AVAILABLE}")
    print(f"Chat history length: {len(langchain_history)}")
    print(f"use_agent: {use_agent}")
    print(f"=" * 50)
    # ⬆️ SAMPAI SINI

    # Initialize response
    bot_reply = None

    # Try agent first if applicable
    if use_agent:
        with st.status("💼 Financial Agent Active", expanded=True) as status:
            st.write("🔍 Menganalisis query finansial...")
            st.write("📝 Checking conversation context...")
            st.write("🛠️ Memilih tools yang sesuai...")

            bot_reply = get_bot_response_with_agent(prompt, rag_context)

            if bot_reply:
                status.update(label="✅ Processing complete", state="complete")
            else:
                st.write("⚠️ Agent tidak dapat menangani query ini")
                status.update(label="⚠️ Falling back to standard mode", state="complete")

    # Fallback to standard response if agent didn't handle it
    if bot_reply is None:
        print("ℹ️ Using standard response (agent returned None or not applicable)")
        bot_reply = get_bot_response_standard(prompt, rag_context)

    # Tampilkan balasan bot
    st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
    with st.chat_message("assistant"):
        st.markdown(bot_reply)

    # Simpan session
    save_current_session()

def render_chat_interface():
    """
    Render complete chat interface
    Main function called from main.py
    """
    # Display existing chat history
    display_chat_history()

    # Show agent status in sidebar
    with st.sidebar:
        st.markdown("---")
        st.subheader("🤖 Agent Status")

        if SECTORS_AVAILABLE:
            st.success("✅ Financial Agent: **Active**")
            with st.expander("🛠️ Available Tools", expanded=False):
                st.markdown("""
                **Market Data:**
                - 📊 Stock Information
                - 📈 Top Stocks (Market Cap)
                - 💰 Top Stocks (Transaction)
                - 🎯 Market Movers
                - 📊 Most Traded Stocks
                
                **Reference Data:**
                - 🏢 Sector/Subsector Lists
                - 🔍 Company Search
                """)
        else:
            st.error("❌ Financial Agent: **Inactive**")
            st.caption("Set SECTORS_API_KEY to enable")

    # Chat input
    if prompt := st.chat_input("💬 Ketik pesan Anda di sini..."):
        handle_user_message(prompt)