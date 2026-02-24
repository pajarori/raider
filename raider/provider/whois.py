import whois, asyncio
from datetime import datetime

class WhoisProvider:
    name = "Whois"
    weight = 0.20

    def _pick_date(self, value):
        if not value:
            return None
        if isinstance(value, list):
            for v in value:
                if isinstance(v, datetime):
                    return v
            return None
        if isinstance(value, datetime):
            return value
        return None

    def _days_since(self, dt):
        from datetime import timezone
        if dt is None:
            return None
        try:
            if dt.tzinfo is not None:
                return (datetime.now(timezone.utc) - dt).days
            return (datetime.now() - dt).days
        except Exception:
            return None

    def _days_until(self, dt):
        from datetime import timezone
        if dt is None:
            return None
        try:
            if dt.tzinfo is not None:
                return (dt - datetime.now(timezone.utc)).days
            return (dt - datetime.now()).days
        except Exception:
            return None
        
    async def analyze(self, client, domain: str):
        try:
            domain_info = await asyncio.to_thread(
                whois.whois,
                domain,
                quiet=True,
                ignore_socket_errors=True,
            )

            created = self._pick_date(getattr(domain_info, "creation_date", None))
            updated = self._pick_date(getattr(domain_info, "updated_date", None))
            expires = self._pick_date(
                getattr(domain_info, "expiration_date", None) or getattr(domain_info, "expiry_date", None)
            )

            age_days = self._days_since(created)
            updated_days_ago = self._days_since(updated)
            expires_in_days = self._days_until(expires)
            registrar = getattr(domain_info, "registrar", None)

            if age_days is None and expires_in_days is None and updated_days_ago is None:
                return None

            return {
                "age_days": age_days,
                "updated_days_ago": updated_days_ago,
                "expires_in_days": expires_in_days,
                "has_registrar": bool(registrar),
            }
        except Exception:
            pass

        return None

    def normalize(self, value):
        if value is None:
            return 0

        if isinstance(value, (int, float)):
            return min(100, (value / 3650) * 100)

        age_days = value.get("age_days")
        updated_days_ago = value.get("updated_days_ago")
        expires_in_days = value.get("expires_in_days")
        has_registrar = value.get("has_registrar", False)

        score = 0

        if age_days is not None and age_days > 0:
            score += min(55, (age_days / 3650) * 55)

        if expires_in_days is not None:
            if expires_in_days <= 0:
                score += 0
            elif expires_in_days >= 365:
                score += 20
            else:
                score += (expires_in_days / 365) * 20

        if updated_days_ago is not None:
            if updated_days_ago >= 365:
                score += 15
            elif updated_days_ago >= 90:
                score += 10
            elif updated_days_ago >= 30:
                score += 6
            elif updated_days_ago >= 7:
                score += 3
            else:
                score += 1

        fields_present = 0
        for v in [age_days, updated_days_ago, expires_in_days]:
            if v is not None:
                fields_present += 1
        score += (fields_present / 3) * 5

        if has_registrar:
            score += 5

        return min(100, score)
