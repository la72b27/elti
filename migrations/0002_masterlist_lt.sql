-- Lift Talk MasterList enrichment table
-- One row per (TC, Pfx, Block) — populated by upload_lt.py
-- Joined onto records at read time to enrich alarm rows with LT metadata
CREATE TABLE IF NOT EXISTS masterlist_lt (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tc              TEXT NOT NULL,
    pfx             TEXT NOT NULL,
    block           TEXT NOT NULL,
    town_council    TEXT,
    full_add        TEXT,
    postal_code     TEXT,
    lift_names_all  TEXT,
    interface       TEXT,
    lss             TEXT,
    UNIQUE (tc, pfx, block)
);
