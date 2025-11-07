import os, tempfile, streamlit as st
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

def load_pdf(uploaded_file) -> List[Document]:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        loader = PyPDFLoader(tmp_path)
        docs = loader.load()
        os.unlink(tmp_path)
        return docs
    except Exception as e:
        st.error(f"Gagal memuat PDF: {e}")
        return []

def split_documents(docs: List[Document], chunk_size=1000, chunk_overlap=200):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(docs)

def create_vectorstore(docs: List[Document]):
    try:
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
        return FAISS.from_documents(docs, embeddings)
    except Exception as e:
        st.error(f"Gagal membuat vectorstore: {e}")
        return None

def retrieve_context(vectorstore, query: str, top_k=3):
    try:
        retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
        docs = retriever.invoke(query)
        context = "\n\n".join([d.page_content for d in docs])
        sources = [d.metadata.get("source", "Unknown") for d in docs]
        return context, sources
    except Exception as e:
        st.error(f"Gagal retrieve context: {e}")
        return "", []