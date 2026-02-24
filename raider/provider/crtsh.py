import httpx

class CrtShProvider:
    name = "CrtSh"
    weight = 0.10

    def __init__(self):
        self.url = "https://crt.sh/"
        
    async def analyze(self, client: httpx.AsyncClient, domain: str):
        try:
            response = await client.get(
                self.url,
                params={
                    "q": f"%.{domain}",
                    "output": "json",
                    "exclude": "expired",
                    "deduplicate": "Y",
                },
                timeout=httpx.Timeout(15.0, connect=5.0)
            )
            
            if response.status_code == 200:
                data = response.json()
                subdomains = set()
                for entry in data:
                    name = entry.get('common_name', '').lower()
                    if name.startswith("*."):
                        name = name[2:]
                    if name.endswith(domain):
                        subdomains.add(name)
                    name_value = entry.get('name_value', '').lower()
                    if name_value:
                        for n in name_value.split('\n'):
                            n = n.strip()
                            if n.startswith("*."):
                                n = n[2:]
                            if n.endswith(domain):
                                subdomains.add(n)
                return len(subdomains)
        except (httpx.HTTPError, ValueError, TypeError):
            return None
            
        return None

    def normalize(self, value):
        if value is None:
            return 0
        return min(100, (value / 500) * 100)
