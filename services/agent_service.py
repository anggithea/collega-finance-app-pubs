"""
LangChain Agent Service untuk Collega AI
Manual tool routing dengan dynamic ticker detection
FIXED: Quarterly financials year parameter
"""
from typing import List, Optional
import re
from datetime import datetime
from difflib import SequenceMatcher
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config.settings import get_llm
from services.groq_service import get_chat_response

# Import tools
try:
    from services.sectors_tools import (
        get_stock_info,
        get_top_stocks_by_market_cap,
        get_companies_by_subsector,
        get_companies_by_index,
        search_companies,
        get_subsector_report,
        get_company_segments,
        get_market_news,
        get_idx_market_cap_history,
        get_quarterly_financials
    )
    from services.sectors_service import SectorsAPI
    SECTORS_AVAILABLE = True

    try:
        sectors_api = SectorsAPI()
        print("✅ Sectors API initialized in agent_service")
    except Exception as e:
        print(f"⚠️ Sectors API initialization failed: {e}")
        sectors_api = None
except Exception as e:
    print(f"Warning: Sectors tools not available - {e}")
    SECTORS_AVAILABLE = False
    sectors_api = None


_COMPANY_CACHE = None


def get_all_companies() -> List[dict]:
    """Get and cache all companies from Sectors API"""
    global _COMPANY_CACHE

    if _COMPANY_CACHE is not None:
        return _COMPANY_CACHE

    if not sectors_api:
        return []

    try:
        companies = sectors_api.get_companies(n_stock=200)

        if isinstance(companies, list) and companies:
            _COMPANY_CACHE = companies
            print(f"✅ Cached {len(companies)} companies")
            return companies

        all_companies = []
        common_subsectors = [
            'banks', 'telecommunication', 'energy', 'consumer-goods',
            'mining', 'property', 'infrastructure', 'finance'
        ]

        for subsector in common_subsectors:
            try:
                companies = sectors_api.get_companies_by_subsector(subsector, n_stock=50)
                if isinstance(companies, list):
                    all_companies.extend(companies)
            except:
                continue

        _COMPANY_CACHE = all_companies
        print(f"✅ Cached {len(all_companies)} companies (fallback method)")
        return all_companies

    except Exception as e:
        print(f"Error getting companies: {e}")
        return []


def find_ticker_by_name(company_name: str) -> Optional[str]:
    """Find ticker by fuzzy matching company name"""
    if not company_name:
        return None

    companies = get_all_companies()

    if not companies:
        return None

    company_name_lower = company_name.lower().strip()
    best_match = None
    best_score = 0.0

    for company in companies:
        name = company.get("company_name", "").lower()
        ticker = company.get("symbol", "")

        if ticker.lower() == company_name_lower:
            return ticker

        score = SequenceMatcher(None, company_name_lower, name).ratio()

        if company_name_lower in name:
            score = max(score, 0.85)

        if score > best_score:
            best_score = score
            best_match = ticker

    if best_score > 0.7:
        print(f"🎯 Found ticker: {best_match} (confidence: {best_score:.2%})")
        return best_match

    return None


def extract_ticker(text: str) -> Optional[str]:
    """Extract stock ticker from text with smart detection"""

    quick_map = {
        "bca": "BBCA",
        "bank bca": "BBCA",
        "pt bank central asia": "BBCA",
        "bri": "BBRI",
        "bank bri": "BBRI",
        "bank rakyat indonesia": "BBRI",
        "mandiri": "BMRI",
        "bank mandiri": "BMRI",
        "telkom": "TLKM",
        "telkomsel": "TLKM",
        "astra": "ASII",
        "goto": "GOTO",
        "gojek": "GOTO",
        "tokopedia": "GOTO",
        "bukalapak": "BUKA",
        "buka": "BUKA",
        "unilever": "UNVR",
        "indofood": "INDF",
        "adaro": "ADRO",
    }

    text_lower = text.lower()

    for key, ticker in quick_map.items():
        if key in text_lower:
            print(f"✅ Quick match found: {key} -> {ticker}")
            return ticker

    text_upper = text.upper()
    match = re.search(r'\b([A-Z]{4})\b', text_upper)
    if match:
        potential_ticker = match.group(1)
        common_words = ["DARI", "YANG", "AKAN", "INFO", "DATA", "HARI", "SAYA", "BANK",
                       "JUGA", "ATAU", "KATA", "BISA", "MANA", "INI"]
        if potential_ticker not in common_words:
            print(f"✅ Explicit ticker found: {potential_ticker}")
            return potential_ticker

    words = text.split()
    potential_names = []

    for word in words:
        if len(word) > 3 and word[0].isupper():
            potential_names.append(word)

    for i in range(len(words)):
        for j in range(i+1, min(i+4, len(words)+1)):
            phrase = " ".join(words[i:j])
            if len(phrase) > 3:
                potential_names.append(phrase)

    print(f"🔍 Potential company names: {potential_names}")

    for name in potential_names:
        ticker = find_ticker_by_name(name)
        if ticker:
            return ticker

    print(f"❌ No ticker found in text: {text}")
    return None


def detect_intent_and_route(user_input: str, chat_history: List = None) -> tuple[str, dict]:
    """
    Detect user intent and route to appropriate tool
    
    PERBAIKAN:
    1.  Prioritas diubah: Cek 'top_market_cap' (general) SEBELUM 'stock_info' (spesifik).
    2.  Logika 'top_market_cap' diperluas untuk mengenali "top 5 perusahaan" 
        atau "saham terbesar", tidak hanya "market cap".
    3.  Logika 'stock_info' disederhanakan menjadi "jaring pengaman" (fallback) 
        jika ticker terdeteksi tapi tidak ada intent lain yang cocok.
    """
    text_lower = user_input.lower()

    # Ekstraksi ticker tetap berjalan, tapi kita tidak akan langsung menurutinya
    ticker = extract_ticker(user_input)
    print(f"🔍 Ticker extraction: {ticker}")

    # ======================================================================
    # LANGKAH 1: Cek Intent General (Non-Ticker) Prioritas Tinggi
    # ======================================================================

    # 1. Top Companies (Top Market Cap)
    # Ini harus dicek SEBELUM stock_info, untuk menangkap "top 5 perusahaan"
    # dan mengabaikan ticker 'AGRO.JK' yang salah terdeteksi.
    top_words = ["top", "terbesar", "tertinggi", "ranking", "papan atas"]
    mcap_words = ["market cap", "kapitalisasi", "nilai pasar"]
    # Pemicu baru: "perusahaan", "saham", "emiten"
    entity_words = ["perusahaan", "saham", "emiten"] 

    is_top_request = any(word in text_lower for word in top_words)
    is_mcap_context = any(word in text_lower for word in mcap_words)
    is_entity_context = any(word in text_lower for word in entity_words)

    # Jika ini permintaan "top" DAN (menyebut "market cap" ATAU "perusahaan/saham")
    if is_top_request and (is_mcap_context or is_entity_context):
        number = 5 # Default
        match = re.search(r'\b(\d+)\b', user_input)
        if match:
            # Ambil angka pertama yang ditemukan (misal "top 5", "top 10")
            number = min(int(match.group(1)), 50)
        
        print("✅ Routing to top_market_cap (Prioritized)")
        return ("top_market_cap", {"limit": number})

    # ======================================================================
    # LANGKAH 2: Cek Intent Ticker-Spesifik (Jika Ticker Ditemukan)
    # ======================================================================
    
    if ticker:
        # 2. Quarterly/Financial Data Request
        if any(
            word in text_lower for word in ["quarter", "kuartal", "q1", "q2", "q3", "q4", "quarterly", "triwulan"]
        ):
            quarter = None
            year = None

            # Extract quarter
            quarter_match = re.search(r'(?:quarter|q|kuartal)\s*(\d)', text_lower)
            if quarter_match:
                quarter = int(quarter_match.group(1))

            # Extract year
            year_match = re.search(r'20\d{2}', user_input)
            if year_match:
                year = int(year_match.group(0))
            else:
                if quarter:
                    year = datetime.now().year
                    print(f"ℹ️ No year specified, using current year: {year}")

            if quarter or year:
                print(f"📅 Quarterly request: Q{quarter} {year}")
                return ("quarterly_financials", {"ticker": ticker, "quarter": quarter, "year": year})

        # 3. Company Segments
        if any(word in text_lower for word in ["segmen", "segment", "bisnis", "breakdown", "pembagian"]):
            return ("company_segments", {"ticker": ticker})

        # 4. News (jika ada ticker)
        if any(word in text_lower for word in ["berita", "news", "kabar"]):
            return ("market_news", {"query": ticker, "limit": 10})

        # 5. Stock Info (Sebagai Fallback/Jaring Pengaman)
        # Jika ada ticker, tapi BUKAN request kuartal, segmen, atau news,
        # maka kita asumsikan user ingin info umum saham tersebut.
        # Kita tidak perlu lagi cek 'not_ranking' karena 'top_market_cap' sudah dicek duluan.
        print(f"✅ Routing to stock_info (Fallback for ticker): {ticker}")
        return ("stock_info", {"ticker": ticker})

    # ======================================================================
    # LANGKAH 3: Cek Intent General Lainnya (Jika Ticker TIDAK Ditemukan)
    # ======================================================================

    # 6. News (general)
    if any(word in text_lower for word in ["berita", "news", "kabar"]):
        return ("market_news", {"query": None, "limit": 10})

    # 7. Index queries
    index_keywords = ["lq45", "lq 45", "idx30", "idx 30", "kompas100"]
    for keyword in index_keywords:
        if keyword in text_lower:
            index_name = keyword.replace(" ", "").upper()
            return ("companies_by_index", {"index": index_name, "limit": 20})

    # 8. Subsector queries
    subsector_map = {
        "bank": "banks",
        "banking": "banks",
        "perbankan": "banks",
        "telekomunikasi": "telecommunication",
        "energi": "energy",
        "tambang": "mining",
    }

    for keyword, subsector in subsector_map.items():
        if keyword in text_lower:
            if any(word in text_lower for word in ["laporan", "report", "analisis"]):
                return ("subsector_report", {"subsector": subsector})
            return ("companies_subsector", {"subsector": subsector, "limit": 20})

    # Jika semua gagal
    print(f"⚠️ No intent matched")
    return ("unknown", {})


def execute_tool(intent: str, params: dict) -> Optional[str]:
    """Execute the appropriate tool based on intent"""
    try:
        print(f"🔧 Executing tool: {intent} with params: {params}")

        if intent == "stock_info":
            result = get_stock_info.invoke(params)
            print(f"📊 Stock info result preview: {result[:200] if result else 'None'}...")
            return result

        elif intent == "quarterly_financials":
            result = get_quarterly_financials.invoke(params)
            print(f"📊 Quarterly financials result preview: {result[:200] if result else 'None'}...")
            return result

        elif intent == "company_segments":
            result = get_company_segments.invoke(params)
            print(f"📊 Company segments result preview: {result[:200] if result else 'None'}...")
            return result

        elif intent == "market_news":
            result = get_market_news.invoke(params)
            print(f"📊 Market news result preview: {result[:200] if result else 'None'}...")
            return result

        elif intent == "top_market_cap":
            result = get_top_stocks_by_market_cap.invoke(params)
            print(f"📊 Top market cap result preview: {result[:200] if result else 'None'}...")
            return result

        elif intent == "companies_by_index":
            result = get_companies_by_index.invoke(params)
            print(f"📊 Companies by index result preview: {result[:200] if result else 'None'}...")
            return result

        elif intent == "companies_subsector":
            result = get_companies_by_subsector.invoke(params)
            print(f"📊 Companies subsector result preview: {result[:200] if result else 'None'}...")
            return result

        elif intent == "subsector_report":
            result = get_subsector_report.invoke(params)
            print(f"📊 Subsector report result preview: {result[:200] if result else 'None'}...")
            return result

        elif intent == "idx_market_cap_history":
            result = get_idx_market_cap_history.invoke(params)
            print(f"📊 IDX market cap history result preview: {result[:200] if result else 'None'}...")
            return result

        else:
            print(f"⚠️ Unknown intent: {intent}")
            return None

    except Exception as e:
        error_msg = f"❌ Error executing tool: {str(e)}"
        print(error_msg)
        return None


def run_agent(user_input: str, chat_history: List = None, rag_context: str = "") -> Optional[str]:
    """Run agent with manual tool routing + LLM context resolution"""
    try:
        resolved_query = resolve_query_with_context(user_input, chat_history)

        intent, params = detect_intent_and_route(resolved_query, chat_history)

        print(f"🔍 Intent detected: {intent}")
        print(f"📋 Params: {params}")

        if intent != "unknown":
            tool_result = execute_tool(intent, params)

            print(f"✅ Tool executed, result length: {len(str(tool_result)) if tool_result else 0}")

            if tool_result and not tool_result.startswith("❌"):
                system_prompt = f"""You are Collega AI Assistant, a helpful financial chatbot specializing in Indonesian stock market.

ORIGINAL USER QUESTION: "{user_input}"
(Note: This may have been resolved from context to: "{resolved_query}")

RAW DATA FROM FINANCIAL DATABASE:
{tool_result}

INSTRUCTIONS:
1. Answer the ORIGINAL question naturally, as if continuing the conversation
2. Extract relevant information from the raw data above
3. Present in Bahasa Indonesia with proper formatting
4. If the user said "saham ini" or similar pronouns, use them naturally in your response
5. Format numbers with thousand separators (Rp)
6. Highlight key metrics that answer the question
7. Keep response concise but informative

Now, provide a natural conversational response:"""

                if rag_context:
                    system_prompt += f"""

ADDITIONAL CONTEXT FROM UPLOADED DOCUMENTS:
{rag_context}
"""

                messages = [
                    {"role": "system", "content": system_prompt},
                ]

                if chat_history:
                    for msg in chat_history[-5:]:
                        if isinstance(msg, HumanMessage):
                            messages.append({"role": "user", "content": msg.content})
                        elif isinstance(msg, AIMessage):
                            messages.append({"role": "assistant", "content": msg.content})

                messages.append({"role": "user", "content": user_input})

                response = get_chat_response(messages)
                return response

        print(f"⚠️ No tool matched or tool failed, returning None for fallback")
        return None

    except Exception as e:
        print(f"❌ Agent error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def is_financial_query(user_input: str, chat_history: List = None) -> bool:
    """Detect if query is financial-related with CONTEXT AWARENESS"""
    if not SECTORS_AVAILABLE:
        print("⚠️ SECTORS_AVAILABLE is False")
        return False

    text_lower = user_input.lower()

    specific_financial_terms = [
        "saham", "stock", "emiten", "ticker", "ihsg", "idx", "bursa",
        "per", "pbv", "roe", "roa", "market cap", "kapitalisasi",
        "gainer", "loser", "volume", "transaksi",
        "bbca", "bbri", "bmri", "tlkm", "asii", "unvr", "goto", "buka",
        "adro", "indf", "icbp", "klbf", "eraa", "antm", "ptba",
        "bank bca", "bank bri", "bank mandiri", "bank rakyat",
        "lq45", "lq 45", "idx30", "kompas100",
        "perbankan", "telekomunikasi", "tambang", "properti", "energi",
        "berita saham", "info saham", "harga saham",
        "finansial", "financial", "laporan", "quarter", "kuartal"
    ]

    has_financial_term = any(term in text_lower for term in specific_financial_terms)

    ticker = extract_ticker(user_input)

    context_ticker = None
    if not ticker and chat_history:
        for msg in reversed(chat_history[-5:]):
            if isinstance(msg, (HumanMessage, AIMessage)):
                potential_ticker = extract_ticker(msg.content)
                if potential_ticker:
                    context_ticker = potential_ticker
                    print(f"🔍 Found context ticker: {context_ticker}")
                    break

    intent, _ = detect_intent_and_route(user_input, chat_history)

    result = has_financial_term or ticker is not None or context_ticker is not None or intent != "unknown"

    print(f"🔍 Financial query check:")
    print(f"   - Has financial term: {has_financial_term}")
    print(f"   - Ticker found: {ticker}")
    print(f"   - Context ticker: {context_ticker}")
    print(f"   - Intent: {intent}")
    print(f"   - Result: {result}")

    return result


def resolve_query_with_context(user_input: str, chat_history: List = None) -> str:
    """Use LLM to resolve ambiguous queries with chat context"""
    if not chat_history or len(chat_history) < 2:
        return user_input

    recent_context = []
    for msg in chat_history[-5:]:
        if isinstance(msg, HumanMessage):
            recent_context.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            recent_context.append(f"Assistant: {msg.content[:200]}...")

    context_str = "\n".join(recent_context)

    resolution_prompt = f"""You are a context resolver. Given a conversation history and a new user query, your job is to rewrite the query to include all necessary context.

CONVERSATION HISTORY:
{context_str}

NEW USER QUERY: "{user_input}"

TASK:
If the user query refers to something from previous messages (like "saham ini", "perusahaan tersebut", "data quarter", etc.), rewrite the query to include the full context (ticker symbol, company name, etc.).

If the query is already complete and clear, return it as-is.

OUTPUT FORMAT:
Return ONLY the resolved query text, nothing else. No explanation, no markdown.

RESOLVED QUERY:"""

    try:
        messages = [
            {"role": "system",
             "content": "You are a context resolver. Return only the resolved query, no explanation."},
            {"role": "user", "content": resolution_prompt}
        ]

        resolved_query = get_chat_response(messages).strip()

        print(f"🔄 Query resolution:")
        print(f"   Original: {user_input}")
        print(f"   Resolved: {resolved_query}")

        return resolved_query

    except Exception as e:
        print(f"⚠️ Context resolution failed: {e}")
        return user_input