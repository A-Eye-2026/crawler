CREATE TABLE IF NOT EXISTS weather_indices (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    area_no       TEXT    NOT NULL,
    area_name     TEXT    NOT NULL,
    lat           REAL    NOT NULL,
    lng           REAL    NOT NULL,
    request_code  TEXT    NOT NULL,
    index_value   REAL,
    published_at  TEXT    NOT NULL,
    synced_at     TEXT    NOT NULL,
    UNIQUE(area_no, request_code, published_at)
);

CREATE INDEX IF NOT EXISTS idx_wi_request_code
    ON weather_indices(request_code);

CREATE INDEX IF NOT EXISTS idx_wi_area_no
    ON weather_indices(area_no);
