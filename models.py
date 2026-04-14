import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse


class Database:
    """SQLite 전용 DB 헬퍼."""

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
        raise ValueError("sqlite:/// 형식만 지원합니다.")

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
        CREATE TABLE IF NOT EXISTS weather_indices (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            area_no       TEXT    NOT NULL,
            area_name     TEXT    NOT NULL,
            lat           REAL    NOT NULL,
            lng           REAL    NOT NULL,
            request_code  TEXT    NOT NULL,
            index_value   REAL,
            forecast_json TEXT,
            published_at  TEXT    NOT NULL,
            synced_at     TEXT    NOT NULL,
            UNIQUE(area_no, request_code, published_at)
        );

        CREATE INDEX IF NOT EXISTS idx_wi_request_code
            ON weather_indices(request_code);

        CREATE INDEX IF NOT EXISTS idx_wi_area_no
            ON weather_indices(area_no);
        """
        with self.connection() as conn:
            conn.executescript(ddl)
            # 기존 DB에 forecast_json 컬럼이 없을 경우 마이그레이션
            try:
                conn.execute("ALTER TABLE weather_indices ADD COLUMN forecast_json TEXT")
            except Exception:
                pass  # 이미 존재하면 무시

    def upsert_weather_indices(self, rows: Iterable[Dict]) -> None:
        row_list = list(rows)
        if not row_list:
            print("[DB] 저장할 데이터가 0건입니다.")
            return

        sql = """
        INSERT INTO weather_indices
            (area_no, area_name, lat, lng, request_code,
             index_value, forecast_json, published_at, synced_at)
        VALUES
            (:area_no, :area_name, :lat, :lng, :request_code,
             :index_value, :forecast_json, :published_at, :synced_at)
        ON CONFLICT(area_no, request_code, published_at) DO UPDATE SET
            index_value   = excluded.index_value,
            forecast_json = excluded.forecast_json,
            synced_at     = excluded.synced_at
        """
        with self.connection() as conn:
            conn.executemany(sql, row_list)
        print(f"[DB] {len(row_list)}건 저장/업데이트 완료")

    def get_weather_indices(self, request_code: str) -> List[Dict]:
        sql = """
        SELECT area_no, area_name, lat, lng, request_code,
               index_value, forecast_json, published_at, synced_at
        FROM   weather_indices
        WHERE  request_code = ?
        ORDER  BY area_name ASC
        """
        with self.connection() as conn:
            rows = conn.execute(sql, (request_code,)).fetchall()

        result = []
        for r in rows:
            row_dict = dict(r)
            raw = row_dict.pop("forecast_json", None)
            try:
                row_dict["forecast"] = json.loads(raw) if raw else {}
            except Exception:
                row_dict["forecast"] = {}
            result.append(row_dict)
        return result

    def get_last_sync_time(self, request_code: str) -> Optional[str]:
        sql = "SELECT MAX(synced_at) AS latest FROM weather_indices WHERE request_code = ?"
        with self.connection() as conn:
            row = conn.execute(sql, (request_code,)).fetchone()
        return row["latest"] if row and row["latest"] else None
