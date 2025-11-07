import os
from dotenv import load_dotenv
from groq import Groq
from langchain_groq import ChatGroq

load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SECTORS_API_KEY = os.getenv("SECTORS_API_KEY")

# Groq Client (untuk legacy functions jika diperlukan)
client = Groq(api_key=GROQ_API_KEY)


# LangChain Groq LLM
def get_llm(model="llama-3.3-70b-versatile", temperature=0.1):
    """
    Get LangChain ChatGroq instance

    Args:
        model: Model name
        temperature: Creativity level (0-1)

    Returns:
        ChatGroq: LangChain LLM instance
    """
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model=model,
        temperature=temperature
    )