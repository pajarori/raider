import asyncio
import threading
from tranco import Tranco
from ..utils import get_cache_dir

class TrancoProvider:
    name = "Tranco"
    weight = 0.40

    def __init__(self):
        self.list = None
        self._init_attempted = False
        self._lock = threading.Lock()
    
    def get(self):
        return self.list

    def _ensure_list(self):
        if self.list is not None:
            return self.list

        with self._lock:
            if self.list is not None:
                return self.list
            if self._init_attempted:
                return None

            try:
                self.list = Tranco(cache=True, cache_dir=get_cache_dir()).list()
            except Exception:
                self.list = None
            finally:
                self._init_attempted = True

        return self.list

    async def analyze(self, client, domain: str):
        tranco_list = await asyncio.to_thread(self._ensure_list)
        if tranco_list is None:
            return None
        try:
            r = tranco_list.rank(domain)
            return r if r != -1 else None
        except Exception:
            return None

    def normalize(self, value):
        if value is None:
            return 0
        return max(0, 100 * (1 - (value / 1_000_000)))
