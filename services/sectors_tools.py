"""
LangChain Tools untuk Sectors.app API
Memungkinkan AI agent untuk menggunakan financial data
"""
from langchain_core.tools import tool
from typing import Optional, Literal
from services.sectors_service import (
    SectorsAPI,
    format_company_overview,
    format_companies_list,
    format_news
)
import os
import re
from datetime import datetime


# Initialize Sectors API client
sectors_client = None
try:
    api_key = os.getenv("SECTORS_API_KEY")
    print("Sectors API key: {}".format(api_key))
    if api_key:
        sectors_client = SectorsAPI(api_key=api_key)
        print("✅ Sectors API client initialized successfully")
    else:
        print("⚠️ SECTORS_API_KEY not found in environment variables")
except Exception as e:
    print(f"❌ Error initializing Sectors API: {e}")


@tool
def get_stock_info(ticker: str) -> str:
    """
    Get comprehensive information about an Indonesian stock company.
    Returns RAW JSON data.

    Args:
        ticker: Stock ticker symbol (e.g., 'BBCA', 'BBRI', 'TLKM')

    Returns:
        Raw JSON data as string
    """
    if not sectors_client:
        return "❌ Sectors API not configured."

    try:
        # Request with sections parameter to get comprehensive data
        data = sectors_client.get_company_overview(ticker.upper(), sections="overview")
        return format_company_overview(data)
    except Exception as e:
        return f"❌ Error fetching stock info: {str(e)}"


@tool
def get_top_stocks_by_market_cap(limit: int = 5, sector: Optional[str] = None) -> str:
    """
    Get top Indonesian stocks ranked by market capitalization.

    Args:
        limit: Number of stocks to return (1-50, default 5)
        sector: Optional sector filter

    Returns:
        Raw JSON array
    """
    if not sectors_client:
        return "❌ Sectors API not configured."

    try:
        limit = max(1, min(limit, 50))

        # Using updated API parameters
        data = sectors_client.get_companies_top(
            n_stock=limit
        )

        return format_companies_list(
            data if isinstance(data, list) else data.get('data', []),
            "Top Companies by Market Cap"
        )
    except Exception as e:
        return f"❌ Error fetching top stocks: {str(e)}"


@tool
def get_companies_by_subsector(subsector: str, limit: int = 20) -> str:
    """
    Get all companies in a specific subsector.

    Args:
        subsector: Subsector name (e.g., 'banks', 'telecommunication')
        limit: Number of results (default 20)

    Returns:
        List of companies in the specified subsector
    """
    if not sectors_client:
        return "❌ Sectors API not configured."

    try:
        limit = max(1, min(limit, 200))
        data = sectors_client.get_companies_by_subsector(
            subsector.lower(),
            n_stock=limit
        )
        return format_companies_list(data, f"Companies in {subsector.title()} subsector")
    except Exception as e:
        return f"❌ Error fetching companies: {str(e)}"


@tool
def get_companies_by_index(index: str, limit: int = 20) -> str:
    """
    Get companies that belong to a specific stock index.

    Args:
        index: Index name (e.g., 'LQ45', 'IDX30', 'KOMPAS100')
        limit: Number of results (default 20)

    Returns:
        List of companies in the specified index
    """
    if not sectors_client:
        return "❌ Sectors API not configured."

    try:
        limit = max(1, min(limit, 200))
        data = sectors_client.get_companies_by_index(
            index.upper(),
            n_stock=limit
        )
        return format_companies_list(data, f"Companies in {index.upper()} index")
    except Exception as e:
        return f"❌ Error fetching index data: {str(e)}"


@tool
def search_companies(
    sub_sector: str = "all",
    min_mcap_billion: int = 5000,
    limit: int = 10
) -> str:
    """
    Search and filter companies.

    Args:
        sub_sector: Subsector filter (default 'all')
        min_mcap_billion: Minimum market cap in billions (default 5000)
        limit: Number of results (default 10)

    Returns:
        List of companies matching the criteria
    """
    if not sectors_client:
        return "❌ Sectors API not configured."

    try:
        limit = max(1, min(limit, 200))
        data = sectors_client.get_companies(
            sub_sector=sub_sector,
            min_mcap_billion=min_mcap_billion,
            n_stock=limit
        )
        return format_companies_list(data, "Search Results")
    except Exception as e:
        return f"❌ Error searching companies: {str(e)}"


@tool
def get_subsector_report(subsector: str) -> str:
    """
    Get comprehensive analysis report for a specific subsector.

    Args:
        subsector: Subsector name (e.g., 'finance', 'energy', 'technology')

    Returns:
        Detailed subsector report
    """
    if not sectors_client:
        return "❌ Sectors API not configured."

    try:
        data = sectors_client.get_subsector_report(subsector.lower())

        if isinstance(data, dict) and "error" in data:
            return f"❌ Error: {data['error']}"

        result = f"📊 **Subsector Report: {subsector.title()}**\n\n"

        if isinstance(data, dict):
            for key, value in data.items():
                if key not in ['error', 'companies']:
                    result += f"**{key.replace('_', ' ').title()}:** {value}\n"

        return result.strip()
    except Exception as e:
        return f"❌ Error fetching subsector report: {str(e)}"


@tool
def get_company_segments(ticker: str) -> str:
    """
    Get revenue and cost segments breakdown for a company.

    Args:
        ticker: Stock ticker (e.g., 'BBCA', 'BBRI')

    Returns:
        Company's revenue and cost segments
    """
    if not sectors_client:
        return "❌ Sectors API not configured."

    try:
        ticker = ticker.upper().replace(".JK", "")
        data = sectors_client.get_company_segments(ticker)

        if isinstance(data, dict) and "error" in data:
            return f"❌ Error: {data['error']}"

        result = f"📊 **Business Segments: {ticker}**\n\n"

        if isinstance(data, dict):
            if 'revenue_segments' in data:
                result += "**Revenue Segments:**\n"
                for segment in data['revenue_segments']:
                    result += f"  • {segment.get('name', 'N/A')}: {segment.get('value', 0):,.0f}\n"
                result += "\n"

            if 'cost_segments' in data:
                result += "**Cost Segments:**\n"
                for segment in data['cost_segments']:
                    result += f"  • {segment.get('name', 'N/A')}: {segment.get('value', 0):,.0f}\n"

        return result.strip()
    except Exception as e:
        return f"❌ Error fetching segments: {str(e)}"


@tool
def get_market_news(query: Optional[str] = None, limit: int = 10) -> str:
    """
    Get latest market news and updates.

    Args:
        query: Optional search query
        limit: Number of news items (default 10)

    Returns:
        List of recent news articles
    """
    if not sectors_client:
        return "❌ Sectors API not configured."

    try:
        data = sectors_client.get_news(query=query, order="desc")

        if isinstance(data, list):
            data = data[:limit]

        return format_news(data)
    except Exception as e:
        return f"❌ Error fetching news: {str(e)}"


@tool
def get_idx_market_cap_history(start_date: str, end_date: str) -> str:
    """
    Get historical IDX market capitalization data.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Historical market cap data
    """
    if not sectors_client:
        return "❌ Sectors API not configured."

    try:
        data = sectors_client.get_idx_total(start=start_date, end=end_date)

        if isinstance(data, dict) and "error" in data:
            return f"❌ Error: {data['error']}"

        if isinstance(data, list) and data:
            result = f"📊 **IDX Market Cap History ({start_date} to {end_date})**\n\n"
            show_count = min(5, len(data))

            for entry in data[:show_count]:
                date = entry.get('date', 'N/A')
                market_cap = entry.get('market_cap', 0)
                result += f"• {date}: Rp {market_cap:,.0f}\n"

            if len(data) > show_count * 2:
                result += f"\n... ({len(data) - show_count * 2} more entries) ...\n\n"

                for entry in data[-show_count:]:
                    date = entry.get('date', 'N/A')
                    market_cap = entry.get('market_cap', 0)
                    result += f"• {date}: Rp {market_cap:,.0f}\n"

            return result.strip()

        return "Tidak ada data ditemukan untuk periode tersebut."
    except Exception as e:
        return f"❌ Error fetching market cap data: {str(e)}"


@tool
def get_quarterly_financials(ticker: str, quarter: Optional[int] = None, year: Optional[int] = None) -> str:
    """
    Get quarterly financial statements for a company.

    Args:
        ticker: Stock ticker (e.g., 'BBCA', 'BBRI')
        quarter: Quarter number (1-4), optional
        year: Year (e.g., 2025), optional

    Returns:
        Raw JSON with quarterly financial data
    """
    if not sectors_client:
        return "❌ Sectors API not configured."

    try:
        ticker = ticker.upper().replace(".JK", "")

        # If year not specified, use current year
        if quarter and not year:
            year = datetime.now().year

        # Get all quarterly data (last 8 quarters)
        data = sectors_client.get_quarterly_financials(ticker, n_quarters=8)

        import json

        # DEBUG: Print first item to see structure
        if isinstance(data, list) and len(data) > 0:
            print(f"📊 DEBUG - First item keys: {list(data[0].keys())}")
            print(f"📊 DEBUG - First item sample: {json.dumps(data[0], indent=2)[:500]}")
        elif isinstance(data, dict):
            print(f"📊 DEBUG - Response is dict with keys: {list(data.keys())}")
            print(f"📊 DEBUG - Dict sample: {json.dumps(data, indent=2)[:500]}")

        # If specific quarter/year requested, filter the data
        if isinstance(data, list) and (quarter or year):
            filtered_data = []
            for item in data:
                item_quarter = None
                item_year = None

                try:
                    # Asumsi format 'date' adalah YYYY-MM-DD
                    date_str = item.get('date')
                    if date_str:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        item_year = date_obj.year
                        item_quarter = (date_obj.month - 1) // 3 + 1 # Logika konversi bulan ke kuartal
                except Exception as e:
                    print(f"⚠️ Gagal parsing date: {e}")
                
                if not item_quarter:
                    item_quarter = item.get('quarter') or item.get('q') or item.get('period_quarter')
                    item_year = item.get('year') or item.get('y') or item.get('period_year')    

                # Also try parsing from period field like "Q3 2024" or "2024-Q3"
                if not item_quarter and 'period' in item:
                    period_str = str(item.get('period', ''))
                    if 'Q' in period_str or 'q' in period_str:
                        q_match = re.search(r'[Qq](\d)', period_str)
                        if q_match:
                            item_quarter = int(q_match.group(1))
                        y_match = re.search(r'20\d{2}', period_str)
                        if y_match:
                            item_year = int(y_match.group(0))

                print(f"🔍 Checking item - quarter: {item_quarter}, year: {item_year}")

                match = True
                if quarter and item_quarter != quarter:
                    match = False
                if year and item_year != year:
                    match = False

                if match:
                    filtered_data.append(item)

            print(f"✅ Found {len(filtered_data)} matching items")

            if filtered_data:
                data = filtered_data
                formatted_json = json.dumps(filtered_data, indent=2, ensure_ascii=False)
                result = f"""
📊 QUARTERLY FINANCIAL DATA
Company: {ticker}
Period: Q{quarter if quarter else 'All'} {year if year else 'All Years'}

{formatted_json}

INSTRUCTIONS: Extract and present quarterly financial metrics including revenue, profit, expenses, margins, etc.
"""
            else:
                # Show what data is available
                available_periods = []
                for item in data:
                    item_quarter = item.get('quarter') or item.get('q') or item.get('period_quarter')
                    item_year = item.get('year') or item.get('y') or item.get('period_year')
                    period = item.get('period', 'Unknown')
                    available_periods.append(f"{period} (Q{item_quarter} {item_year})" if item_quarter and item_year else period)

                result = f"""
❌ Data tidak ditemukan untuk Q{quarter} {year}

Available periods in response:
{chr(10).join(['  - ' + p for p in available_periods[:5]])}

Raw first item:
{json.dumps(data[0], indent=2, ensure_ascii=False)[:500] if data else 'No data'}
"""
        else:
            # Return all data
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            result = f"""
📊 QUARTERLY FINANCIAL DATA
Company: {ticker}
Period: Last 8 Quarters

{formatted_json}

INSTRUCTIONS: Extract and present quarterly financial metrics.
"""

        return result.strip()

    except Exception as e:
        import traceback
        return f"❌ Error fetching quarterly data: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


# Export all tools
SECTORS_TOOLS = [
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
]


__all__ = [
    'get_stock_info',
    'get_top_stocks_by_market_cap',
    'get_companies_by_subsector',
    'get_companies_by_index',
    'search_companies',
    'get_subsector_report',
    'get_company_segments',
    'get_market_news',
    'get_idx_market_cap_history',
    'get_quarterly_financials',
    'SECTORS_TOOLS'
]