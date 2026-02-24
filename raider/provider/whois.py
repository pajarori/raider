import whois, asyncio
from datetime import datetime

class WhoisProvider:
    name = "Whois"
    weight = 0.30
        
    async def analyze(self, client, domain: str):
        try:
            domain_info = await asyncio.to_thread(
                whois.whois,
                domain,
                quiet=True,
                ignore_socket_errors=True,
            )
            
            creation_date = domain_info.creation_date
            
            if not creation_date:
                return None
                
            if isinstance(creation_date, list):
                creation_date = creation_date[0]
                
            if isinstance(creation_date, str):
                return None
                
            from datetime import timezone
            if creation_date.tzinfo is not None:
                age_timedelta = datetime.now(timezone.utc) - creation_date
            else:
                age_timedelta = datetime.now() - creation_date
            return age_timedelta.days
        except Exception:
            pass

        return None

    def normalize(self, value):
        if value is None:
            return 0
        return min(100, (value / 3650) * 100)
