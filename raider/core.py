import asyncio, httpx
from .utils import TIERS
from .provider.tranco import TrancoProvider
from .provider.openpage import OpenPageProvider
from .provider.crtsh import CrtShProvider
from .provider.whois import WhoisProvider

class Raider:
    def __init__(self):
        self.analyzers = {
            "tranco": TrancoProvider(),
            "openpage": OpenPageProvider(),
            "crtsh": CrtShProvider(),
            "whois": WhoisProvider(),
        }
        
    async def analyze(self, client: httpx.AsyncClient, domain: str):
        async def fetch(provider_id, provider):
            try:
                value = await provider.analyze(client, domain)
            except Exception:
                value = None
            return provider_id, provider, value

        tasks = [fetch(provider_id, provider) for provider_id, provider in self.analyzers.items()]
        return await asyncio.gather(*tasks)

    def get_tier(self, score, calculated_providers):
        if calculated_providers == 0:
            return TIERS[-1]

        for tier in TIERS:
            if score >= tier["min_score"]:
                return tier
        return TIERS[-2]

    def get_confidence(self, coverage_ratio):
        if coverage_ratio >= 0.90:
            return "very high"
        if coverage_ratio >= 0.70:
            return "high"
        if coverage_ratio >= 0.50:
            return "medium"
        if coverage_ratio > 0:
            return "low"
        return "none"

    def calculate_score(self, results):
        score = 0
        total_weight = 0
        calculated_providers = 0
        provider_rows = []
        total_provider_count = len(results)
        total_possible_weight = sum(provider.weight for _, provider, _ in results)

        for provider_id, provider, value in results:
            normalized = None
            if value is not None:
                normalized = provider.normalize(value)
                score += normalized * provider.weight
                total_weight += provider.weight
                calculated_providers += 1
            provider_rows.append({
                "id": provider_id,
                "name": provider.name,
                "weight": provider.weight,
                "value": value,
                "normalized": round(normalized, 2) if normalized is not None else None,
                "available": value is not None,
            })

        if total_weight > 0:
            score = (score / total_weight)

        score = round(score, 2)
        provider_coverage_ratio = (calculated_providers / total_provider_count) if total_provider_count else 0.0
        weight_coverage_ratio = (total_weight / total_possible_weight) if total_possible_weight else 0.0
        tier = self.get_tier(score, calculated_providers)

        return {
            "score": score,
            "tier": tier["name"],
            "color": tier["color"],
            "confidence": self.get_confidence(weight_coverage_ratio),
            "coverage": {
            "providers_available": calculated_providers,
            "providers_total": total_provider_count,
            "providers_ratio": round(provider_coverage_ratio, 2),
            "weight_covered": round(total_weight, 2),
            "weight_total": round(total_possible_weight, 2),
            "weight_ratio": round(weight_coverage_ratio, 2),
            },
            "providers": provider_rows,
        }

    def summarize(self, domain, results):
        summary = self.calculate_score(results)
        summary["domain"] = domain
        return summary
