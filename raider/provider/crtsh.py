import httpx, asyncio, threading, queue, time

try:
    import psycopg
except Exception:
    psycopg = None

class CrtShProvider:
    name = "CrtSh"
    weight = 0.10
    pool_size = 6
    sql = """
WITH hits AS (
    SELECT c.id
    FROM certificate c
    WHERE identities(c.certificate) @@ ident_query(%s)
    LIMIT 5000
),
names AS (
    SELECT regexp_replace(trim(x.name), '^\\*\\.', '') AS name
    FROM hits h
    JOIN certificate_and_identities ci ON ci.certificate_id = h.id
    CROSS JOIN LATERAL unnest(string_to_array(lower(ci.name_value), E'\\n')) AS x(name)
)
SELECT COUNT(DISTINCT name)
FROM names
WHERE name = %s OR name LIKE %s;
""".strip()

    def __init__(self):
        self._pg_pool = queue.Queue(maxsize=self.pool_size)
        self._pg_pool_ready = False
        self._pg_disabled = False
        self._pg_init_lock = threading.Lock()
        self._pg_created = 0

    def _connect_pg(self):
        if psycopg is None:
            raise RuntimeError("psycopg not installed")
        conn = psycopg.connect(
            host="crt.sh",
            port=5432,
            dbname="certwatch",
            user="guest",
            connect_timeout=3,
            autocommit=True,
        )
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '25s'")
            cur.execute("SELECT 1")
            row = cur.fetchone()
            if not (row and row[0] == 1):
                raise RuntimeError("crt.sh postgres healthcheck failed")
        return conn

    def _close_conn(self, conn):
        try:
            if conn:
                conn.close()
        except Exception:
            pass

    def _ensure_pg_pool(self):
        if self._pg_disabled or psycopg is None:
            return False
        if self._pg_pool_ready:
            return True

        with self._pg_init_lock:
            if self._pg_pool_ready:
                return True
            try:
                conn = self._connect_pg()
                self._pg_pool.put_nowait(conn)
                self._pg_created = 1
                self._pg_pool_ready = True
                return True
            except Exception:
                self._pg_disabled = True
                return False

    def _replace_conn(self, conn):
        self._close_conn(conn)
        try:
            return self._connect_pg()
        except Exception:
            return None

    def _get_pg_conn(self):
        try:
            return self._pg_pool.get_nowait()
        except queue.Empty:
            pass

        with self._pg_init_lock:
            if self._pg_disabled:
                return None
            if self._pg_created < self.pool_size:
                try:
                    conn = self._connect_pg()
                    self._pg_created += 1
                    self._pg_pool_ready = True
                    return conn
                except Exception:
                    self._pg_disabled = True
                    return None

        try:
            return self._pg_pool.get(timeout=1)
        except queue.Empty:
            return None

    def _pg_count(self, domain: str):
        d = domain.lower()
        if not self._ensure_pg_pool():
            return None

        conn = None
        conn = self._get_pg_conn()
        if conn is None:
            return None

        try:
            for attempt in range(3):
                try:
                    with conn.cursor() as cur:
                        cur.execute("SET statement_timeout = '25s'")
                        cur.execute(self.sql, (d, d, f"%.{d}"))
                        row = cur.fetchone()
                        return int(row[0]) if row and row[0] is not None else 0
                except Exception as e:
                    msg = str(e).lower()
                    transient = (
                        "conflict with recovery" in msg
                        or "canceling statement" in msg
                        or "statement timeout" in msg
                        or "timeout" in msg
                    )

                    if attempt < 2 and transient and not getattr(conn, "closed", False):
                        time.sleep(0.4 * (attempt + 1))
                        continue

                    if attempt < 2 and getattr(conn, "closed", False):
                        conn = self._replace_conn(conn)
                        if conn is None:
                            return None
                        time.sleep(0.2)
                        continue
                    return None
        finally:
            if conn is not None:
                try:
                    self._pg_pool.put_nowait(conn)
                except queue.Full:
                    self._close_conn(conn)

    async def analyze(self, client: httpx.AsyncClient, domain: str):
        return await asyncio.to_thread(self._pg_count, domain)

    def normalize(self, value):
        if value is None:
            return 0
        return min(100, (value / 500) * 100)
