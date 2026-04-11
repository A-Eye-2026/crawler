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
