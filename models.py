import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse


class Database:
    """SQLite 전용 DB 헬퍼.

    현재는 로컬 MVP를 위해 sqlite3를 직접 사용하지만,
    클래스 경계를 명확히 해 두어 추후 SQLAlchemy나 다른 DB 드라이버로 옮기기 쉽도록 했다.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.db_path = self._resolve_sqlite_path(database_url)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _resolve_sqlite_path(database_url: str) -> str:
        if database_url.startswith("sqlite:///"):
            return database_url.replace("sqlite:///", "", 1)
        parsed = urlparse(database_url)
        if parsed.scheme == "sqlite":
            return parsed.path.lstrip("/")
        raise ValueError("현재 MVP는 sqlite:/// 형식만 지원합니다.")

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS rest_areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE,
            name TEXT NOT NULL,
            route_name TEXT,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            total_parking_spaces INTEGER NOT NULL DEFAULT 0,
            occupied_parking_spaces INTEGER NOT NULL DEFAULT 0,
            available_parking_spaces INTEGER NOT NULL DEFAULT 0,
            ev_charger_count INTEGER DEFAULT 0,
            restaurant_congestion_level TEXT,
            source_name TEXT DEFAULT 'ex_api',
            last_synced_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_rest_areas_route_name
        ON rest_areas(route_name);

        CREATE INDEX IF NOT EXISTS idx_rest_areas_last_synced_at
        ON rest_areas(last_synced_at);
        """
        with self.connection() as conn:
            conn.executescript(ddl)

    def upsert_rest_areas(self, rows: Iterable[Dict]) -> None:
        sql = """
        INSERT INTO rest_areas (
            external_id, name, route_name, lat, lng,
            total_parking_spaces, occupied_parking_spaces, available_parking_spaces,
            ev_charger_count, restaurant_congestion_level,
            source_name, last_synced_at, updated_at
        ) VALUES (
            :external_id, :name, :route_name, :lat, :lng,
            :total_parking_spaces, :occupied_parking_spaces, :available_parking_spaces,
            :ev_charger_count, :restaurant_congestion_level,
            :source_name, :last_synced_at, CURRENT_TIMESTAMP
        )
        ON CONFLICT(external_id) DO UPDATE SET
            name = excluded.name,
            route_name = excluded.route_name,
            lat = excluded.lat,
            lng = excluded.lng,
            total_parking_spaces = excluded.total_parking_spaces,
            occupied_parking_spaces = excluded.occupied_parking_spaces,
            available_parking_spaces = excluded.available_parking_spaces,
            ev_charger_count = excluded.ev_charger_count,
            restaurant_congestion_level = excluded.restaurant_congestion_level,
            source_name = excluded.source_name,
            last_synced_at = excluded.last_synced_at,
            updated_at = CURRENT_TIMESTAMP;
        """
        with self.connection() as conn:
            conn.executemany(sql, list(rows))

    def get_rest_areas(self) -> List[Dict]:
        query = """
        SELECT
            id,
            external_id,
            name,
            route_name,
            lat,
            lng,
            total_parking_spaces,
            occupied_parking_spaces,
            available_parking_spaces,
            ev_charger_count,
            restaurant_congestion_level,
            source_name,
            last_synced_at,
            updated_at
        FROM rest_areas
        ORDER BY name ASC
        """
        with self.connection() as conn:
            rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]

    def get_last_sync_time(self) -> Optional[str]:
        query = "SELECT MAX(last_synced_at) AS latest_sync FROM rest_areas"
        with self.connection() as conn:
            row = conn.execute(query).fetchone()
        return row["latest_sync"] if row and row["latest_sync"] else None
