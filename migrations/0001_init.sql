-- ELTI D1 database schema
-- records: one row per (TC, Pfx, Block, RBE) alarm entry
CREATE TABLE IF NOT EXISTS records (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tc            TEXT    NOT NULL,
    pfx           TEXT    NOT NULL,
    block         TEXT    NOT NULL,
    lift          TEXT,
    address       TEXT,
    postcode      TEXT,
    lcoy          TEXT,
    status_date   TEXT,
    rbe           TEXT    NOT NULL,
    rbe_display   TEXT,
    status        INTEGER,
    UNIQUE (tc, pfx, block, rbe)
);

-- meta: scalar key-value store (last_updated, counts, etc.)
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- mask: excluded postcodes (cross-device, same as KV mask_data)
CREATE TABLE IF NOT EXISTS mask (
    postcode TEXT PRIMARY KEY
);
