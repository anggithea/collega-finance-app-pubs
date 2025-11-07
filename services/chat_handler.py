import streamlit as st
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate, \
    HumanMessagePromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from services.groq_service import get_chat_response
from services.rag_pipeline import retrieve_context
from utils.memory import save_current_session


def display_chat_history():
    """
    Menampilkan riwayat chat dari session state
    """
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def build_messages_with_langchain(prompt: str) -> tuple[list, str]:
    """
    Membangun pesan menggunakan LangChain prompts, termasuk konteks RAG jika ada

    Args:
        prompt: Input dari user

    Returns:
        tuple: (messages list, context_text)
    """
    context_text = ""

    # Jika ada vectorstore (RAG aktif)
    if "vectorstore" in st.session_state and st.session_state["vectorstore"] is not None:
        with st.spinner("🔍 Mengambil konteks dari dokumen..."):
            context_text, sources = retrieve_context(st.session_state["vectorstore"], prompt)
            if context_text:
                st.info(f"📚 Ditemukan konteks dari dokumen: {len(sources)} sumber")

    # Definisikan system prompt dengan atau tanpa RAG context
    if context_text:
        system_template = """You are Collega AI Assistant, a friendly and helpful chatbot created to assist users.
Use the following context from the uploaded document to help answer the question:

Context:
{context}

Always base your answer on the provided context when relevant."""

        system_prompt = SystemMessagePromptTemplate.from_template(system_template)

        # Buat prompt template dengan context
        prompt_template = ChatPromptTemplate.from_messages([
            system_prompt,
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{input}")
        ])

        # Format prompt dengan variable
        formatted_prompt = prompt_template.format_messages(
            context=context_text,
            chat_history=convert_chat_history_to_langchain(),
            input=prompt
        )
    else:
        system_template = """You are Collega AI Assistant, a friendly and helpful chatbot created to assist users.
If the user uploaded a document, use that as additional context."""

        system_prompt = SystemMessagePromptTemplate.from_template(system_template)

        # Buat prompt template tanpa context
        prompt_template = ChatPromptTemplate.from_messages([
            system_prompt,
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{input}")
        ])

        # Format prompt dengan variable
        formatted_prompt = prompt_template.format_messages(
            chat_history=convert_chat_history_to_langchain(),
            input=prompt
        )

    # Konversi LangChain messages ke format dict untuk API
    messages = [{"role": msg.type, "content": msg.content} for msg in formatted_prompt]

    # Normalisasi role names (LangChain menggunakan 'human', 'ai', 'system')
    for msg in messages:
        if msg["role"] == "human":
            msg["role"] = "user"
        elif msg["role"] == "ai":
            msg["role"] = "assistant"

    return messages, context_text


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


def get_bot_response(messages: list) -> str:
    """
    Mendapatkan response dari bot (Groq API)

    Args:
        messages: List pesan untuk dikirim ke API

    Returns:
        str: Response dari bot
    """
    with st.spinner("🤖 Collega AI sedang menjawab..."):
        try:
            bot_reply = get_chat_response(messages)
        except Exception as e:
            bot_reply = f"⚠️ Terjadi kesalahan saat memanggil API Groq: {e}"

    return bot_reply


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

    # Build messages dengan LangChain prompts dan RAG context jika ada
    messages, _ = build_messages_with_langchain(prompt)

    # Dapatkan response dari bot
    bot_reply = get_bot_response(messages)

    # Tampilkan balasan bot
    st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
    with st.chat_message("assistant"):
        st.markdown(bot_reply)

    # Simpan session
    save_current_session()