"""
Service untuk integrasi dengan Sectors.app API
Dokumentasi: https://docs.sectors.app/
"""
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import os


class SectorsAPI:
    """Client untuk Sectors Financial API"""

    BASE_URL = "https://api.sectors.app/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Sectors API client

        Args:
            api_key: Sectors API key (default dari environment variable)
        """
        self.api_key = api_key or os.getenv("SECTORS_API_KEY")

        if not self.api_key:
            raise ValueError(
                "SECTORS_API_KEY tidak ditemukan. Set di environment variable atau pass sebagai parameter.")

        self.headers = {
            "Authorization": self.api_key.strip()
        }

        print(f"🔑 API Key configured (first 10 chars): {self.api_key[:10]}...")
        print(f"📋 Headers: {self.headers}")

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Helper untuk membuat API request

        Args:
            endpoint: API endpoint (tanpa base URL)
            params: Query parameters (optional)

        Returns:
            Dict: Response JSON dari API
        """
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            print(f"🌐 API Request: {url}")
            if params:
                print(f"📋 Params: {params}")

            response = requests.get(url, headers=self.headers, params=params, timeout=10)

            print(f"📡 Status Code: {response.status_code}")

            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict):
                print(f"✅ Response keys: {list(data.keys())}")
            elif isinstance(data, list):
                print(f"✅ Response: List with {len(data)} items")

            return data

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                return {"error": "Rate limit exceeded. Tunggu beberapa saat."}
            elif response.status_code == 400:
                return {"error": f"Bad request: {response.text}"}
            elif response.status_code == 404:
                return {"error": f"Endpoint not found: {endpoint}"}
            else:
                return {"error": f"HTTP Error {response.status_code}: {response.text}"}
        except requests.exceptions.Timeout:
            return {"error": "Request timeout. API tidak merespons."}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    # ==================== COMPANIES ====================

    def get_companies(
        self,
        sections: str = "all",
        n_stock: int = 50
    ) -> List[Dict]:
        """
        Get list of companies
        Endpoint: GET /companies/
        """
        params = {
            "sections": sections,
            "n_stock": n_stock
        }

        return self._make_request("companies/", params)

    def get_companies_top(
        self,
        n_stock: int = 10,
        classifications: str = "all",
        year: Optional[int] = None,
        min_mcap_billion: int = 1,
        logic: str = "and",
        include_none: bool = False
    ) -> Dict:
        """
        Get top companies (sesuai dokumentasi API v1)
        Endpoint: GET /companies/top/
        """
        params = {
            "n_stock": n_stock,
            "classifications": classifications,
            "year": year,
            "min_mcap_billion": min_mcap_billion,
            "logic": logic,
            "include_none": str(include_none).lower()
        }
        
        params = {k: v for k, v in params.items() if v is not None}

        return self._make_request("companies/top/", params)

    def get_companies_by_index(
        self,
        index: str,
        sections: str = "all",
        n_stock: int = 50
    ) -> List[Dict]:
        """
        Get companies by stock index
        Endpoint: GET /index/{index}/
        """
        params = {
            "sections": sections,
            "n_stock": n_stock
        }

        return self._make_request(f"index/{index}/", params)

    def get_companies_by_subsector(
        self,
        subsector: str,
        sections: str = "all",
        n_stock: int = 50
    ) -> List[Dict]:
        """
        Get companies by subsector
        """
        params = {
            "sections": sections,
            "n_stock": n_stock,
            "sub_sector": subsector
        }

        return self._make_request("companies/", params)

    # ==================== COMPANY DATA ====================

    def get_company_overview(self, ticker: str, sections: str = "overview") -> Dict:
        """
        Get comprehensive company overview
        Endpoint: GET /company/report/{ticker}/

        Args:
            ticker: Stock ticker
            sections: Sections to include (default: "overview")
                     Options: overview, valuation, future, peers, financials, dividend
        """
        ticker = ticker.upper().replace(".JK", "")
        params = {}
        if sections:
            params["sections"] = sections

        return self._make_request(f"company/report/{ticker}/", params)

    def get_company_segments(self, ticker: str) -> Dict:
        """
        Get revenue and cost segments of a company
        Endpoint: GET /company/get-segments/{ticker}/
        """
        ticker = ticker.upper().replace(".JK", "")
        return self._make_request(f"company/get-segments/{ticker}/")

    # ==================== SUBSECTOR ANALYSIS ====================

    def get_subsector_report(self, subsector: str, sections: str = "all") -> Dict:
        """
        Get comprehensive subsector report
        Endpoint: GET /subsector/report/{subsector}/
        """
        params = {}
        if sections:
            params["sections"] = sections

        return self._make_request(f"subsector/report/{subsector}/", params)

    # ==================== MARKET DATA ====================

    def get_idx_total(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> List[Dict]:
        """
        Get historical IDX market capitalization data
        Endpoint: GET /idx-total/
        """
        params = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        return self._make_request("idx-total/", params if params else None)

    # ==================== NEWS ====================

    def get_news(
        self,
        query: Optional[str] = None,
        sources: Optional[str] = None,
        from_date: Optional[str] = None,
        order: str = "desc"
    ) -> List[Dict]:
        """
        Get market news
        Endpoint: GET /news/
        """
        params = {"order": order}
        if query:
            params["query"] = query
        if sources:
            params["sources"] = sources
        if from_date:
            params["from"] = from_date

        return self._make_request("news/", params)

    def get_quarterly_financials(
        self,
        ticker: str,
        n_quarters: int = 8
    ) -> Dict:
        """
        Get quarterly financial data for a company
        Endpoint: GET /financials/quarterly/{ticker}/

        Args:
            ticker: Stock ticker
            n_quarters: Number of quarters to retrieve (default 8)

        Note: This endpoint returns all quarters. Filter by quarter/year in application code.
        """
        ticker = ticker.upper().replace(".JK", "")
        endpoint = f"financials/quarterly/{ticker}/"

        params = {
            "n_quarters": n_quarters
        }

        return self._make_request(endpoint, params)


# ==================== HELPER FUNCTIONS ====================

def format_company_overview(data: Dict) -> str:
    """Return raw data sebagai string yang mudah dibaca AI"""
    if "error" in data:
        return f"❌ Error: {data['error']}"

    try:
        print(f"\n🔍 Raw data keys: {list(data.keys())}")
        import json
        formatted_json = json.dumps(data, indent=2, ensure_ascii=False)

        result = f"""
DATA SAHAM (Raw API Response):

{formatted_json}

CATATAN: Data di atas adalah response langsung dari API Sectors.app.
Silakan extract dan present informasi yang relevan sesuai pertanyaan user.
"""
        return result.strip()

    except Exception as e:
        return f"❌ Error formatting data: {str(e)}\n\nRaw response: {str(data)[:1000]}"


def format_companies_list(data: List[Dict], title: str = "Companies") -> str:
    """Return raw companies list untuk AI processing"""
    if isinstance(data, dict) and "error" in data:
        return f"❌ Error: {data['error']}"

    try:
        if not data:
            return "Tidak ada data perusahaan ditemukan."

        import json
        limited_data = data[:20] if len(data) > 20 else data
        formatted_json = json.dumps(limited_data, indent=2, ensure_ascii=False)

        result = f"""
{title.upper()} (Total: {len(data)} companies, showing {len(limited_data)}):

{formatted_json}

CATATAN: Silakan present data ini dalam format yang user-friendly.
"""
        return result.strip()

    except Exception as e:
        return f"❌ Error formatting data: {str(e)}"


def format_news(data: List[Dict]) -> str:
    """Return raw news list untuk AI processing"""
    if isinstance(data, dict) and "error" in data:
        return f"❌ Error: {data['error']}"

    try:
        if not data:
            return "Tidak ada berita ditemukan."

        import json
        limited_data = data[:10] if len(data) > 10 else data
        formatted_json = json.dumps(limited_data, indent=2, ensure_ascii=False)

        result = f"""
BERITA TERKINI (Total: {len(data)} articles, showing {len(limited_data)}):

{formatted_json}

CATATAN: Silakan summarize berita-berita ini dalam format yang mudah dibaca.
"""
        return result.strip()

    except Exception as e:
        return f"❌ Error formatting data: {str(e)}"