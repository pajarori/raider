import tldextract
from pathlib import Path
from . import __version__

VERSION = __version__

TIERS = [
    {
        "name": "high",
        "min_score": 80,
        "min_coverage": 0.75,
        "color": "green",
        "desc": "Strong signal with broad provider coverage",
    },
    {
        "name": "medium",
        "min_score": 50,
        "min_coverage": 0.50,
        "color": "yellow",
        "desc": "Moderate score and/or partial coverage",
    },
    {
        "name": "low",
        "min_score": 1,
        "min_coverage": 0.0,
        "color": "red",
        "desc": "Weak signal or very limited evidence",
    },
    {
        "name": "no data",
        "min_score": 0,
        "min_coverage": 0.0,
        "color": "dim",
        "desc": "Provider data unavailable",
    },
]

def get_package_dir():
    return Path(__file__).parent

def get_data_dir():
    data_dir = Path.home() / ".local" / "pajarori" / "raider"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_cache_dir():
    cache_dir = get_data_dir() / ".cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir

def get_tld_extractor():
    tld_cache_dir = get_cache_dir() / "tldextract"
    tld_cache_dir.mkdir(exist_ok=True)
    return tldextract.TLDExtract(cache_dir=str(tld_cache_dir), suffix_list_urls=())

def is_safe_domain(domain):
    if not domain:
        return False
    d = domain.lower()
    return not any(c not in "abcdefghijklmnopqrstuvwxyz0123456789.-" for c in d)
