# services/__init__.py
from .groq_service import get_chat_response
from .rag_pipeline import retrieve_context
from .document_handler import handle_document_upload

# Optional - Sectors API
try:
    from .sectors_service import SectorsAPI
    from .sectors_tools import SECTORS_TOOLS
    __all__ = [
        'get_chat_response',
        'retrieve_context',
        'handle_document_upload',
        'SectorsAPI',
        'SECTORS_TOOLS'
    ]
except ImportError:
    __all__ = [
        'get_chat_response',
        'retrieve_context',
        'handle_document_upload'
    ]