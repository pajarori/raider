import os, httpx

class OpenPageProvider:
    name = "OpenPage"
    weight = 0.30

    def __init__(self):
        self.api_url = "https://openpagerank.com/api/v1.0/getPageRank"
        self.api_key = "8cwwkw44gs8wsowkw844kg0wowg4s88ks044c8kc" # use it as you want bro, i dont care

    async def analyze(self, client: httpx.AsyncClient, domain: str):
        if not self.api_key:
            return None
        try:
            response = await client.get(
                self.api_url,
                params={"domains[]": domain},
                headers={"API-OPR": self.api_key},
                timeout=10.0
            )
            if response.status_code == 200:
                rows = response.json().get("response", [])
                if not rows:
                    return None
                r = rows[0].get("page_rank_decimal")
                return float(r) if r else None
        except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError):
            return None
        return None

    def normalize(self, value):
        if value is None:
            return 0
        return value * 10
