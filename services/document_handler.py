import streamlit as st
from services.rag_pipeline import load_pdf, split_documents, create_vectorstore


def handle_document_upload():
    """
    Menangani upload dan pemrosesan dokumen PDF untuk RAG
    """
    uploaded_file = st.file_uploader(
        "📄 Upload file PDF (opsional untuk konteks tambahan)",
        type=["pdf"]
    )

    if uploaded_file is not None:
        with st.spinner("Memproses dokumen..."):
            docs = load_pdf(uploaded_file)
            split_docs = split_documents(docs)
            vectorstore = create_vectorstore(split_docs)
            st.session_state["vectorstore"] = vectorstore

        st.success("✅ Dokumen berhasil diproses dan siap digunakan untuk konteks RAG!")