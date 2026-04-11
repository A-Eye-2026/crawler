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
        """데이터를 DB에 삽입하거나 이미 존재하면 업데이트한다."""
        row_list = list(rows)
        if not row_list:
            print("[DB] 저장할 데이터가 0건입니다.")
            return

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
        try:
            with self.connection() as conn:
                conn.executemany(sql, row_list)
                print(f"[DB] {len(row_list)}건의 데이터가 성공적으로 저장/업데이트되었습니다.")
        except Exception as e:
            print(f"[DB] 저장 중 오류 발생: {e}")
            raise

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

    def search_rest_areas(self, query_text: str) -> List[Dict]:
        """이름 또는 노선명으로 휴게소를 검색한다."""
        sql = """
        SELECT * FROM rest_areas
        WHERE name LIKE ? OR route_name LIKE ?
        ORDER BY name ASC
        """
        search_term = f"%{query_text}%"
        with self.connection() as conn:
            rows = conn.execute(sql, (search_term, search_term)).fetchall()
        return [dict(row) for row in rows]

    def get_last_sync_time(self) -> Optional[str]:
        query = "SELECT MAX(last_synced_at) AS latest_sync FROM rest_areas"
        with self.connection() as conn:
            row = conn.execute(query).fetchone()
        return row["latest_sync"] if row and row["latest_sync"] else None
